import logging
import os
import re
import tempfile
import time
from urllib.parse import urlparse, urlunparse

import httpx

from exceptions import FileTooLargeError, SsrfBlockedError
from utils import _is_safe_url

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

VALID_CONTENT_TYPES = frozenset({
    "application/epub+zip",
    "application/pdf",
    "application/x-mobipocket-ebook",
    "application/octet-stream",
})


def sanitize_ext(ext: str) -> str:
    cleaned = re.sub(r'[^a-z0-9]', '', (ext or '').lower())[:10]
    return cleaned or 'epub'


def redact_url(url: str) -> str:
    """Strip query params from logged URLs (may contain auth tokens)."""
    try:
        p = urlparse(url)
        return urlunparse(p._replace(query="[redacted]" if p.query else ""))
    except Exception:
        return "[url]"


async def check_redirect(response: httpx.Response) -> None:
    """httpx hook: block redirects to internal IPs (SSRF protection on redirects)."""
    if response.is_redirect:
        location = str(response.headers.get("location", ""))
        if location and not _is_safe_url(location):
            raise SsrfBlockedError(f"Redirect blocked (SSRF): {redact_url(location)}")


async def stream_to_temp_file(resp: httpx.Response, ext: str, progress_callback=None, max_bytes: int = 0) -> str | None:
    """Stream an already-open httpx response to a temp file with progress updates."""
    total = int(resp.headers.get("content-length", 0))
    downloaded = 0
    last_report = 0.0
    last_pct = -1
    suffix = f".{ext}" if ext else ".epub"
    path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="maman_") as f:
            path = f.name
            async for chunk in resp.aiter_bytes(65536):
                f.write(chunk)
                downloaded += len(chunk)
                if max_bytes and downloaded > max_bytes:
                    raise FileTooLargeError(f"File too large (>{max_bytes // 1024 // 1024} MB)")
                if progress_callback:
                    now = time.monotonic()
                    pct = int(downloaded / total * 100) if total else 0
                    if now - last_report >= 2.0 and pct != last_pct:
                        last_report = now
                        last_pct = pct
                        try:
                            await progress_callback(downloaded, total)
                        except Exception:
                            pass
        if downloaded < 1024:
            os.remove(path)
            return None
        return path
    except FileTooLargeError:
        raise
    except Exception as e:
        logger.warning(f"Stream to file failed: {e}")
        if path:
            try:
                os.remove(path)
            except Exception:
                pass
        return None
