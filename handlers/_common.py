from telegram import Update
from telegram.ext import ContextTypes

from config import Config
from i18n import t
from models import DownloadState


def _state(context: ContextTypes.DEFAULT_TYPE) -> DownloadState:
    if "state" not in context.user_data:
        context.user_data["state"] = DownloadState()
    return context.user_data["state"]


def _is_allowed(update: Update, config: Config) -> bool:
    uid = update.effective_user.id if update.effective_user else None
    return uid in config.allowed_user_ids


def _fmt_size(size_bytes: int, lang: str = "fr") -> str:
    if not size_bytes:
        return "?"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.0f} {t('fmt.kb', lang)}"
    return f"{size_bytes / 1024 / 1024:.1f} {t('fmt.mb', lang)}"
