import httpx
import logging

from models import SearchResult

logger = logging.getLogger(__name__)


def _guess_ext(item: dict) -> str:
    title = (item.get("title") or "").lower()
    for ext in ["epub", "pdf", "mobi", "azw3"]:
        if ext in title:
            return ext
    return "epub"


async def search(query: str, url: str, api_key: str) -> list[SearchResult]:
    """Search Prowlarr for books. Returns list of SearchResult."""
    if not url:
        return []
    params = {
        "query": query,
        "categories[]": ["7000", "7020"],
        "type": "search",
    }
    async with httpx.AsyncClient(
        base_url=url,
        headers={"X-Api-Key": api_key},
        timeout=20,
    ) as client:
        try:
            resp = await client.get("/api/v1/search", params=params)
            resp.raise_for_status()
            items = resp.json()
        except Exception as e:
            logger.error(f"Prowlarr search failed: {e}")
            return []

    results = []
    for item in items:
        dl_url = item.get("downloadUrl") or ""
        guid = item.get("guid") or ""
        if not dl_url and not guid:
            continue

        magnet = item.get("magnetUrl") or ""
        is_torrent = (
            dl_url.endswith(".torrent")
            or bool(magnet)
            or item.get("downloadProtocol", "").lower() == "torrent"
        )

        results.append(SearchResult(
            source="prowlarr",
            title=item.get("title") or "",
            author="",
            ext=_guess_ext(item),
            size_bytes=item.get("size") or 0,
            guid=guid,
            indexer_id=item.get("indexerId") or 0,
            download_url=dl_url,
            magnet_url=magnet,
            is_torrent=is_torrent,
            seeders=item.get("seeders") or 0,
            md5="",
        ))

    return results


async def grab(indexer_id: int, guid: str, url: str, api_key: str) -> None:
    """Tell Prowlarr to grab (send to download client) a result by guid."""
    payload = {"guid": guid, "indexerId": indexer_id}
    async with httpx.AsyncClient(
        base_url=url,
        headers={"X-Api-Key": api_key},
        timeout=20,
    ) as client:
        try:
            resp = await client.post("/api/v1/download", json=payload)
            resp.raise_for_status()
            logger.info(f"Prowlarr grab successful for guid={guid}")
        except Exception as e:
            logger.error(f"Prowlarr grab failed: {e}")
            raise
