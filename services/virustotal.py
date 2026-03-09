import asyncio
import hashlib
import logging
import os

import httpx

from exceptions import VirusTotalError

logger = logging.getLogger(__name__)

_VT_BASE = "https://www.virustotal.com/api/v3"
_VT_MAX_SIZE = 32 * 1024 * 1024


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


async def scan_file(file_path: str, api_key: str) -> dict | None:
    """
    Scan a file with VirusTotal. Returns stats dict or None if api_key empty or file too large.
    Stats keys: malicious, suspicious, undetected, harmless, timeout, failure, type-unsupported.
    """
    if not api_key:
        return None

    size = os.path.getsize(file_path)
    if size > _VT_MAX_SIZE:
        logger.info(f"VirusTotal: file too large ({size / 1024 / 1024:.1f} MB), skipping scan")
        return None

    headers = {"x-apikey": api_key}

    async with httpx.AsyncClient(headers=headers) as client:
        sha256 = await asyncio.get_running_loop().run_in_executor(None, _sha256, file_path)
        resp = await client.get(f"{_VT_BASE}/files/{sha256}", timeout=15)
        if resp.status_code == 200:
            stats = resp.json()["data"]["attributes"]["last_analysis_stats"]
            logger.info(f"VirusTotal: existing report for {sha256[:12]}... — {stats}")
            return stats

        logger.info(f"VirusTotal: uploading file ({size / 1024 / 1024:.1f} MB)...")
        with open(file_path, "rb") as f:
            resp = await client.post(
                f"{_VT_BASE}/files",
                files={"file": (os.path.basename(file_path), f)},
                timeout=120,
            )
        resp.raise_for_status()
        analysis_id = resp.json()["data"]["id"]

        for _ in range(18):
            await asyncio.sleep(5)
            resp = await client.get(f"{_VT_BASE}/analyses/{analysis_id}", timeout=15)
            resp.raise_for_status()
            data = resp.json()["data"]
            if data["attributes"]["status"] == "completed":
                stats = data["attributes"]["stats"]
                logger.info(f"VirusTotal: analysis complete — {stats}")
                return stats

    raise VirusTotalError("VirusTotal analysis timed out after 90 s")
