import asyncio
import logging
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import prefs
from config import Config
from handlers._common import _is_allowed, _state
from i18n import get_lang, t

logger = logging.getLogger(__name__)


def _settings_text(user_prefs: dict, lang: str) -> str:
    not_configured = t("settings.not_configured", lang)
    fmt = user_prefs.get("format", "epub")
    email = user_prefs.get("email", not_configured)
    kindle = user_prefs.get("kindle_email", not_configured)
    stored_lang = user_prefs.get("lang", lang)
    return t("settings.title", lang, fmt=fmt.upper(), email=email, kindle=kindle, lang=stored_lang)


def _settings_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("settings.btn_format", lang), callback_data="setfmt_menu")],
        [InlineKeyboardButton(t("settings.btn_email", lang), callback_data="setemail_prompt")],
        [InlineKeyboardButton(t("settings.btn_kindle", lang), callback_data="setkindl_prompt")],
        [InlineKeyboardButton(t("settings.btn_lang", lang), callback_data="setlang_menu")],
        [InlineKeyboardButton(t("settings.btn_delete", lang), callback_data="prefs_delete_confirm")],
    ])


async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /settings command."""
    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    user_id = update.effective_user.id
    user_prefs = await prefs.get(user_id)
    lang = get_lang(update, user_prefs)
    await update.message.reply_text(
        _settings_text(user_prefs, lang), parse_mode="Markdown", reply_markup=_settings_keyboard(lang)
    )


async def handle_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    user_id = update.effective_user.id
    user_prefs = await prefs.get(user_id)
    lang = get_lang(update, user_prefs)
    await query.edit_message_text(
        _settings_text(user_prefs, lang), parse_mode="Markdown", reply_markup=_settings_keyboard(lang)
    )


async def handle_setfmt_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    user_id = update.effective_user.id
    user_prefs = await prefs.get(user_id)
    lang = get_lang(update, user_prefs)
    current_fmt = user_prefs.get("format", "epub")

    buttons = []
    for fmt in ["epub", "pdf", "mobi", "azw3"]:
        if fmt in config.allowed_formats:
            marker = "* " if fmt == current_fmt else ""
            buttons.append([InlineKeyboardButton(f"{marker}{fmt.upper()}", callback_data=f"setfmt_{fmt}")])

    buttons.append([InlineKeyboardButton(t("settings.btn_back", lang), callback_data="open_settings")])
    keyboard = InlineKeyboardMarkup(buttons)

    await query.edit_message_text(t("settings.format_prompt", lang), reply_markup=keyboard)


async def handle_setfmt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    user_id = update.effective_user.id
    user_prefs = await prefs.get(user_id)
    lang = get_lang(update, user_prefs)
    m = re.match(r"^setfmt_(\w+)$", query.data or "")
    if not m:
        return

    fmt = m.group(1)
    await prefs.set(user_id, "format", fmt)

    await query.edit_message_text(t("settings.format_set", lang, fmt=fmt.upper()), parse_mode="Markdown")
    await asyncio.sleep(1)
    await handle_settings(update, context)


async def handle_setemail_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    user_id = update.effective_user.id
    user_prefs = await prefs.get(user_id)
    lang = get_lang(update, user_prefs)
    _state(context).waiting_for = "email"
    await query.edit_message_text(t("settings.email_prompt", lang))


async def handle_setkindl_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    user_id = update.effective_user.id
    user_prefs = await prefs.get(user_id)
    lang = get_lang(update, user_prefs)
    _state(context).waiting_for = "kindle_email"
    await query.edit_message_text(t("settings.kindle_prompt", lang), parse_mode="Markdown")


async def handle_prefs_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    user_id = update.effective_user.id
    user_prefs = await prefs.get(user_id)
    lang = get_lang(update, user_prefs)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(t("settings.btn_delete_yes", lang), callback_data="prefs_delete_execute")],
        [InlineKeyboardButton(t("settings.btn_delete_no", lang), callback_data="open_settings")],
    ])

    await query.edit_message_text(t("settings.delete_confirm", lang), reply_markup=keyboard)


async def handle_prefs_delete_execute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    user_id = update.effective_user.id
    user_prefs = await prefs.get(user_id)
    lang = get_lang(update, user_prefs)
    await prefs.delete_user(user_id)
    _state(context).waiting_for = ""

    await query.edit_message_text(t("settings.deleted", lang))


async def handle_setlang_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    user_id = update.effective_user.id
    user_prefs = await prefs.get(user_id)
    lang = get_lang(update, user_prefs)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Francais", callback_data="setlang_fr"),
            InlineKeyboardButton("English", callback_data="setlang_en"),
        ],
        [InlineKeyboardButton(t("settings.btn_back", lang), callback_data="open_settings")],
    ])
    await query.edit_message_text(t("settings.lang_prompt", lang), reply_markup=keyboard)


async def handle_setlang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    m = re.match(r"^setlang_(fr|en)$", query.data or "")
    if not m:
        return

    lang_code = m.group(1)
    user_id = update.effective_user.id
    await prefs.set(user_id, "lang", lang_code)

    confirmation_key = "settings.lang_set_fr" if lang_code == "fr" else "settings.lang_set_en"
    await query.edit_message_text(t(confirmation_key, lang_code))
    await asyncio.sleep(1)
    await handle_settings(update, context)
