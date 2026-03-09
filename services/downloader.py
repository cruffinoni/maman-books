import logging

import httpx

from config import Config
from exceptions import DownloadError, FileTooLargeError
from http_utils import HEADERS, VALID_CONTENT_TYPES, sanitize_ext, check_redirect, redact_url, stream_to_temp_file
from models import SearchResult
from utils import _is_safe_url
from services import anna_archive, prowlarr, watcher

logger = logging.getLogger(__name__)


async def download_result(result: SearchResult, progress_callback=None, max_bytes: int = 0, config: Config | None = None) -> str:
    """
    Download a search result to a temp file and return its path.
    Handles Anna's Archive, Prowlarr direct, and Prowlarr torrent.
    """
    ext = sanitize_ext(result.ext)

    if result.source == "anna":
        base_url = config.anna_archive_url if config else ""
        return await anna_archive.download(result.md5, ext, base_url, progress_callback, max_bytes=max_bytes)

    if result.source == "prowlarr":
        if result.is_torrent:
            prowlarr_url = config.prowlarr_url if config else ""
            prowlarr_api_key = config.prowlarr_api_key if config else ""
            download_path = config.books_download_path if config else "/downloads/books"
            timeout_minutes = config.download_timeout_minutes if config else 15
            return await _download_torrent(result, prowlarr_url, prowlarr_api_key, download_path, timeout_minutes)
        else:
            return await _download_direct(result.download_url, ext, progress_callback, max_bytes=max_bytes)

    raise DownloadError(f"Unknown source: {result.source!r}")


async def _download_direct(url: str, ext: str, progress_callback=None, max_bytes: int = 0) -> str:
    """Stream a direct download URL to a temp file."""
    if not _is_safe_url(url):
        raise DownloadError("URL rejected (SSRF protection)")
    ext = sanitize_ext(ext)
    async with httpx.AsyncClient(
        headers=HEADERS, timeout=60, follow_redirects=True,
        event_hooks={"response": [check_redirect]},
    ) as client:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            ctype = resp.headers.get("content-type", "").split(";")[0].strip()
            if ctype and ctype not in VALID_CONTENT_TYPES:
                raise DownloadError(f"Unexpected content-type: {ctype!r}")
            path = await stream_to_temp_file(resp, ext, progress_callback, max_bytes)
            if path is None:
                raise DownloadError("Download produced an empty or invalid file")
            return path


async def _download_torrent(result: SearchResult, prowlarr_url: str, prowlarr_api_key: str, download_path: str, timeout_minutes: int) -> str:
    """Grab via Prowlarr and watch download folder for the resulting file."""
    await prowlarr.grab(result.indexer_id, result.guid, prowlarr_url, prowlarr_api_key)
    path = await watcher.wait_for_file(result.title, download_path, timeout_minutes)
    return path
