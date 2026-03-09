import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

from handlers import onboarding, settings, search, download

logger = logging.getLogger(__name__)


async def _global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled exception in handler", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "Une erreur interne s'est produite. Reessaie."
            )
        except Exception:
            pass


def register_all_handlers(app: Application) -> None:
    """Register all Telegram handlers on the application."""
    app.add_handler(CommandHandler("start", onboarding.start))
    app.add_handler(CommandHandler("settings", settings.cmd_settings))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search.handle_search))
    app.add_handler(CallbackQueryHandler(download.handle_download, pattern=r"^dl_\d+$"))
    app.add_handler(CallbackQueryHandler(download.handle_download_fmt, pattern=r"^dlfmt_(epub|pdf|mobi|azw3)_\d+$"))
    app.add_handler(CallbackQueryHandler(download.handle_dest_telegram, pattern=r"^dest_telegram_\d+$"))
    app.add_handler(CallbackQueryHandler(download.handle_dest_email, pattern=r"^dest_email_\d+$"))
    app.add_handler(CallbackQueryHandler(download.handle_dest_kindle, pattern=r"^dest_kindle_\d+$"))
    app.add_handler(CallbackQueryHandler(search.handle_confirm_non_epub, pattern=r"^confirm_non_epub$"))
    app.add_handler(CallbackQueryHandler(search.handle_cancel_search, pattern=r"^cancel_search$"))
    app.add_handler(CallbackQueryHandler(download.handle_cancel_download, pattern=r"^cancel_dl$"))
    app.add_handler(CallbackQueryHandler(settings.handle_settings, pattern=r"^open_settings$"))
    app.add_handler(CallbackQueryHandler(settings.handle_setfmt_menu, pattern=r"^setfmt_menu$"))
    app.add_handler(CallbackQueryHandler(settings.handle_setfmt, pattern=r"^setfmt_\w+$"))
    app.add_handler(CallbackQueryHandler(settings.handle_setemail_prompt, pattern=r"^setemail_prompt$"))
    app.add_handler(CallbackQueryHandler(settings.handle_setkindl_prompt, pattern=r"^setkindl_prompt$"))
    app.add_handler(CallbackQueryHandler(settings.handle_prefs_delete_confirm, pattern=r"^prefs_delete_confirm$"))
    app.add_handler(CallbackQueryHandler(settings.handle_prefs_delete_execute, pattern=r"^prefs_delete_execute$"))
    app.add_handler(CallbackQueryHandler(onboarding.handle_onb_fmt, pattern=r"^onb_fmt_\w+$"))
    app.add_handler(CallbackQueryHandler(onboarding.handle_onb_skip_email, pattern=r"^onb_skip_email$"))
    app.add_handler(CallbackQueryHandler(onboarding.handle_onb_skip_kindle, pattern=r"^onb_skip_kindle$"))
    app.add_error_handler(_global_error_handler)
