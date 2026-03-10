import logging
import os
import sys
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_VALID_FORMATS = {"epub", "pdf", "mobi", "azw3"}
_VERSION = "1.5.0"


def _int_env(var: str, default: str) -> int:
    val = os.environ.get(var, default)
    try:
        return int(val)
    except ValueError:
        sys.exit(f"Invalid config: {var} must be an integer, got {val!r}")


@dataclass(frozen=True)
class SmtpConfig:
    host: str
    port: int
    user: str
    password: str
    sender: str

    def is_configured(self) -> bool:
        return bool(self.host and self.user and self.password)


@dataclass(frozen=True)
class Config:
    telegram_token: str
    allowed_user_ids: frozenset[int]
    local_api_server: str
    github_repo: str
    allowed_formats: tuple[str, ...]
    anna_archive_url: str
    prowlarr_url: str
    prowlarr_api_key: str
    books_download_path: str
    download_timeout_minutes: int
    virustotal_api_key: str
    smtp: SmtpConfig
    prefs_file: str
    version: str
    max_results: int
    max_query_length: int
    rate_limit_seconds: int

    @property
    def max_file_size(self) -> int:
        return 400 * 1024 * 1024 if self.local_api_server else 50 * 1024 * 1024

    @classmethod
    def from_env(cls) -> "Config":
        allowed_user_ids: set[int] = set()
        for uid in os.environ.get("ALLOWED_USER_IDS", "").split(","):
            uid = uid.strip()
            if uid:
                try:
                    allowed_user_ids.add(int(uid))
                except ValueError:
                    logger.warning(f"ALLOWED_USER_IDS: ignoring non-numeric value {uid!r}")

        smtp_user = os.environ.get("SMTP_USER", "")
        smtp_from = os.environ.get("SMTP_FROM") or smtp_user
        smtp = SmtpConfig(
            host=os.environ.get("SMTP_HOST", "smtp.gmail.com"),
            port=_int_env("SMTP_PORT", "587"),
            user=smtp_user,
            password=os.environ.get("SMTP_PASSWORD", ""),
            sender=smtp_from,
        )

        raw_formats = os.environ.get("ALLOWED_FORMATS", "epub,pdf").split(",")
        allowed_formats = tuple(
            f for f in (s.strip() for s in raw_formats)
            if f in _VALID_FORMATS
        ) or ("epub",)

        default_prefs_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "user_prefs.json"
        )

        telegram_token = os.environ.get("TELEGRAM_TOKEN") or sys.exit(
            "Missing required env var: TELEGRAM_TOKEN"
        )

        return cls(
            telegram_token=telegram_token,
            allowed_user_ids=frozenset(allowed_user_ids),
            local_api_server=os.environ.get("LOCAL_API_SERVER", "").rstrip("/"),
            github_repo=os.environ.get("GITHUB_REPO", ""),
            allowed_formats=allowed_formats,
            anna_archive_url=os.environ.get("ANNA_ARCHIVE_URL", "").rstrip("/"),
            prowlarr_url=os.environ.get("PROWLARR_URL", "").rstrip("/"),
            prowlarr_api_key=os.environ.get("PROWLARR_API_KEY", ""),
            books_download_path=os.environ.get("BOOKS_DOWNLOAD_PATH", "/downloads/books"),
            download_timeout_minutes=_int_env("DOWNLOAD_TIMEOUT_MINUTES", "15"),
            virustotal_api_key=os.environ.get("VIRUSTOTAL_API_KEY", ""),
            smtp=smtp,
            prefs_file=os.environ.get("USER_PREFS_FILE") or default_prefs_file,
            version=_VERSION,
            max_results=_int_env("MAX_RESULTS", "10"),
            max_query_length=_int_env("MAX_QUERY_LENGTH", "200"),
            rate_limit_seconds=_int_env("RATE_LIMIT_SECONDS", "5"),
        )
