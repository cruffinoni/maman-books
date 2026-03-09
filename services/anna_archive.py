import logging
import re
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup

from exceptions import AllMirrorsFailedError
from http_utils import HEADERS, sanitize_ext, redact_url, check_redirect, stream_to_temp_file
from models import SearchResult
from utils import _is_safe_url

logger = logging.getLogger(__name__)

_MD5_RE = re.compile(r'^[a-f0-9]{32}$')
_MAX_HTML_SIZE = 5 * 1024 * 1024


def _validate_md5(md5: str) -> bool:
    return bool(_MD5_RE.match(md5))


def _is_trusted_url(url: str, base_url: str) -> bool:
    """Like _is_safe_url, but also allows URLs from the same origin as base_url."""
    if base_url:
        parsed = urlparse(url)
        base = urlparse(base_url)
        if parsed.scheme == base.scheme and parsed.netloc == base.netloc:
            return True
    return _is_safe_url(url)


def _parse_size_from_text(text: str) -> int:
    """Try to extract file size in bytes from a text string like '2.3 MB' or '450 KB'."""
    m = re.search(r"([\d.,]+)\s*(MB|KB|GB|Mo|Ko|Go)", text, re.IGNORECASE)
    if not m:
        return 0
    try:
        value = float(m.group(1).replace(",", "."))
        unit = m.group(2).upper()
        if unit in ("KB", "KO"):
            return int(value * 1024)
        if unit in ("MB", "MO"):
            return int(value * 1024 * 1024)
        if unit in ("GB", "GO"):
            return int(value * 1024 * 1024 * 1024)
    except ValueError:
        pass
    return 0


def _extract_download_link(html: str, source_url: str) -> str | None:
    """Extract the real file download link from an intermediate HTML page (e.g. libgen.li/ads.php)."""
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if not href:
            continue
        lower = href.lower()
        if any(lower.endswith(ext) for ext in [".epub", ".pdf", ".mobi", ".azw3", ".fb2"]):
            if href.startswith("http"):
                return href
            return urljoin(source_url, href)
        if "get.php" in lower and "md5" in lower:
            if href.startswith("http"):
                return href
            return urljoin(source_url, href)
    return None


async def _search_html(client: httpx.AsyncClient, query: str, base_url: str) -> list[SearchResult]:
    """Parse Anna's Archive HTML search page."""
    try:
        resp = await client.get(
            f"{base_url}/search",
            params={"q": query, "lang": "", "content": "book_any", "ext": "epub,pdf,mobi"},
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        seen_md5: dict[str, SearchResult] = {}
        for a in soup.select("a[href^='/md5/']"):
            href = a.get("href", "")
            md5 = href.split("/md5/")[-1].split("?")[0].strip()
            if not md5 or not _validate_md5(md5):
                continue
            text = a.get_text(" ", strip=True)
            if not text:
                continue
            if md5 in seen_md5:
                existing = seen_md5[md5]
                if len(text) > len(existing.title):
                    seen_md5[md5] = SearchResult(
                        source=existing.source,
                        title=text[:120],
                        author=existing.author,
                        ext=existing.ext,
                        size_bytes=existing.size_bytes,
                        is_torrent=existing.is_torrent,
                        download_url=existing.download_url,
                        md5=existing.md5,
                        guid=existing.guid,
                        indexer_id=existing.indexer_id,
                        magnet_url=existing.magnet_url,
                        seeders=existing.seeders,
                    )
                continue
            ext = "epub"
            for e in ["epub", "pdf", "mobi"]:
                if e in text.lower():
                    ext = e
                    break
            seen_md5[md5] = SearchResult(
                source="anna",
                title=text[:120],
                author="",
                ext=sanitize_ext(ext),
                size_bytes=_parse_size_from_text(text),
                is_torrent=False,
                download_url="",
                md5=md5,
                guid="",
                indexer_id=0,
                magnet_url="",
                seeders=0,
            )
            if len(seen_md5) >= 10:
                break
        return list(seen_md5.values())
    except Exception as e:
        logger.error(f"Anna's Archive HTML fallback failed: {e}")
        return []


async def search(query: str, base_url: str) -> list[SearchResult]:
    """Search Anna's Archive for books. Returns list of SearchResult."""
    if not base_url:
        return []
    async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True, event_hooks={"response": [check_redirect]}) as client:
        return await _search_html(client, query, base_url)


async def _get_download_links(client: httpx.AsyncClient, md5: str, base_url: str) -> list[str]:
    """Scrape the Anna's Archive book page to get real download links."""
    page_url = f"{base_url}/md5/{md5}"
    try:
        resp = await client.get(page_url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        links = []
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            text = a.get_text(strip=True).lower()
            if any(kw in text for kw in ["download", "telecharger", "get", "mirror", "libgen", "lol"]):
                if href.startswith("http") and md5.lower() in href.lower() and _is_safe_url(href):
                    links.append(href)
            elif href.startswith("http") and md5.lower() in href.lower() and _is_safe_url(href):
                links.append(href)
        links.append(f"{base_url}/slow_download/{md5}/0/0")
        logger.info(f"Found {len(links)} download links for md5={md5}: {[redact_url(u) for u in links]}")
        return links
    except Exception as e:
        logger.warning(f"Could not scrape book page for md5={md5}: {e}")
        return [f"{base_url}/slow_download/{md5}/0/0"]


async def _stream_to_file(client: httpx.AsyncClient, url: str, ext: str, progress_callback=None, max_bytes: int = 0) -> str | None:
    """Open a new streaming GET request and save to file."""
    try:
        async with client.stream("GET", url) as resp:
            if resp.status_code != 200:
                return None
            ctype = resp.headers.get("content-type", "").split(";")[0].strip()
            if "text/html" in ctype:
                return None
            return await stream_to_temp_file(resp, ext, progress_callback, max_bytes)
    except Exception as e:
        logger.warning(f"Stream failed for {redact_url(url)}: {e}")
        return None


async def download(md5: str, ext: str, base_url: str, progress_callback=None, max_bytes: int = 0) -> str:
    """Download a book by md5. Returns path to temp file."""
    ext = sanitize_ext(ext)
    async with httpx.AsyncClient(
        headers=HEADERS, timeout=90, follow_redirects=True,
        event_hooks={"response": [check_redirect]},
    ) as client:
        links = await _get_download_links(client, md5, base_url)
        for url in links:
            try:
                if ".onion" in url or not _is_trusted_url(url, base_url):
                    continue
                logger.info(f"Trying download URL: {redact_url(url)}")
                async with client.stream("GET", url) as resp:
                    if resp.status_code != 200:
                        logger.warning(f"URL {redact_url(url)} returned {resp.status_code}")
                        continue
                    ctype = resp.headers.get("content-type", "").split(";")[0].strip()
                    if "text/html" in ctype:
                        chunks, size = [], 0
                        async for chunk in resp.aiter_bytes(65536):
                            chunks.append(chunk)
                            size += len(chunk)
                            if size > _MAX_HTML_SIZE:
                                logger.warning(f"HTML page too large (>{_MAX_HTML_SIZE // 1024 // 1024} MB), skipping")
                                break
                        html = b"".join(chunks)
                        real_url = _extract_download_link(html.decode("utf-8", errors="ignore"), url)
                        if real_url:
                            if not _is_safe_url(real_url):
                                logger.warning(f"Real link rejected (SSRF): {redact_url(real_url)}")
                                continue
                            logger.info(f"Found real link in HTML: {redact_url(real_url)}")
                            result = await _stream_to_file(client, real_url, ext, progress_callback, max_bytes)
                            if result:
                                return result
                        logger.warning(f"URL {redact_url(url)} returned HTML, no real link found")
                        continue
                    result = await stream_to_temp_file(resp, ext, progress_callback, max_bytes)
                    if result:
                        logger.info(f"Downloaded from {redact_url(url)}")
                        return result
            except Exception as e:
                logger.warning(f"URL {redact_url(url)} failed: {e}")
    raise AllMirrorsFailedError(f"All mirrors failed for md5={md5}")
