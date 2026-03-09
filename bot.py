import asyncio
import glob
import logging
import os
import tempfile

import httpx
from dotenv import load_dotenv
load_dotenv()

from telegram.ext import Application, ContextTypes

from config import Config
from handlers import register_all_handlers

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

_notified_update: str | None = None


def _is_newer_version(remote: str, local: str) -> bool:
    """Return True if remote tag is strictly greater than local version."""
    def parse(v: str) -> tuple:
        try:
            return tuple(int(x) for x in v.lstrip("v").split("."))
        except ValueError:
            return (0,)
    return parse(remote) > parse(local)


def _cleanup_orphaned_temp_files() -> None:
    pattern = os.path.join(tempfile.gettempdir(), "maman_*")
    count = 0
    for path in glob.glob(pattern):
        try:
            os.remove(path)
            count += 1
        except Exception:
            pass
    if count:
        logger.info(f"Cleaned up {count} orphaned temp file(s)")


async def check_for_updates(context: ContextTypes.DEFAULT_TYPE) -> None:
    global _notified_update
    config: Config = context.bot_data["config"]
    if not config.github_repo:
        return
    try:
        async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "maman-books-bot"}) as client:
            resp = await client.get(
                f"https://api.github.com/repos/{config.github_repo}/releases/latest",
                headers={"Accept": "application/vnd.github+json"},
            )
            if resp.status_code == 404:
                return
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning(f"Update check failed: {e}")
        return

    tag = data.get("tag_name", "")
    if not tag or tag == _notified_update or not _is_newer_version(tag, config.version):
        return

    _notified_update = tag
    url = data.get("html_url", f"https://github.com/{config.github_repo}/releases/latest")
    msg = (
        f"Nouvelle version disponible : *{tag}*\n"
        f"Version installee : `{config.version}`\n"
        f"[Voir les changements]({url})"
    )
    for uid in config.allowed_user_ids:
        try:
            await context.bot.send_message(uid, msg, parse_mode="Markdown", disable_web_page_preview=True)
        except Exception as e:
            logger.warning(f"Could not notify user {uid} about update: {e}")


def main() -> None:
    config = Config.from_env()

    builder = Application.builder().token(config.telegram_token)
    if config.local_api_server:
        builder = (
            builder
            .base_url(f"{config.local_api_server}/bot")
            .base_file_url(f"{config.local_api_server}/file/bot")
            .local_mode(True)
        )
        logger.info(f"Local Bot API mode: {config.local_api_server} (limit {config.max_file_size // 1024 // 1024} MB)")

    app = builder.build()
    app.bot_data["config"] = config

    register_all_handlers(app)

    if config.github_repo:
        app.job_queue.run_repeating(check_for_updates, interval=86400, first=30)
        logger.info(f"Update checks enabled for {config.github_repo} (every 24h)")

    _cleanup_orphaned_temp_files()
    if config.anna_archive_url.startswith("http://"):
        logger.warning("ANNA_ARCHIVE_URL uses unencrypted HTTP — HTTPS is recommended")

    from services import converter, virustotal
    import services.mailer  # noqa: F401 — imported here to surface config errors at startup

    logger.info(f"--- maman-books v{config.version} ---")
    logger.info(f"  Anna's Archive : {'enabled: ' + config.anna_archive_url if config.anna_archive_url else 'disabled'}")
    logger.info(f"  Prowlarr       : {'enabled: ' + config.prowlarr_url if config.prowlarr_url else 'disabled'}")
    logger.info(f"  Formats        : {', '.join(config.allowed_formats)}")
    logger.info(f"  VirusTotal     : {'enabled' if config.virustotal_api_key else 'disabled'}")
    logger.info(f"  Calibre        : {'ebook-convert found' if converter.ebook_convert_available() else 'absent - fallback PyMuPDF'}")
    logger.info(f"  Email / Kindle : {'enabled' if config.smtp.is_configured() else 'disabled'}")
    logger.info(f"  Updates        : {'enabled: ' + config.github_repo if config.github_repo else 'disabled'}")
    logger.info(f"  File limit     : {config.max_file_size // 1024 // 1024} MB{'  [local Bot API]' if config.local_api_server else ''}")
    logger.info(f"  Users          : {len(config.allowed_user_ids)} allowed")
    logger.info("Bot started.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
