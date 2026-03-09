import asyncio
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SearchResult:
    source: str
    title: str
    author: str
    ext: str
    size_bytes: int
    is_torrent: bool
    download_url: str
    md5: str
    guid: str
    indexer_id: int
    magnet_url: str
    seeders: int


@dataclass
class DownloadState:
    results: list[SearchResult] = field(default_factory=list)
    pending_format: dict[int, str] = field(default_factory=dict)
    pending_non_epub: bool = False
    waiting_for: str = ""
    onboarding_step: str = ""
    active_dl_task: asyncio.Task | None = None
    last_search_at: float = 0.0
