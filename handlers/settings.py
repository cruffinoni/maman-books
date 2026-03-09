import asyncio
import logging
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import prefs
from config import Config
from handlers._common import _is_allowed, _state

logger = logging.getLogger(__name__)


def _settings_text(user_prefs: dict) -> str:
    fmt = user_prefs.get("format", "epub")
    email = user_prefs.get("email", "non configure")
    kindle = user_prefs.get("kindle_email", "non configure")
    return (
        "*Vos preferences :*\n\n"
        f"• Format par defaut : `{fmt.upper()}`\n"
        f"• Email personnel : `{email if email != 'non configure' else 'non configure'}`\n"
        f"• Adresse Kindle : `{kindle if kindle != 'non configure' else 'non configure'}`"
    )


def _settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Format", callback_data="setfmt_menu")],
        [InlineKeyboardButton("Mon email", callback_data="setemail_prompt")],
        [InlineKeyboardButton("Mon Kindle", callback_data="setkindl_prompt")],
        [InlineKeyboardButton("Supprimer mes donnees", callback_data="prefs_delete_confirm")],
    ])


async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /settings command."""
    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    user_id = update.effective_user.id
    user_prefs = await prefs.get(user_id)
    await update.message.reply_text(
        _settings_text(user_prefs), parse_mode="Markdown", reply_markup=_settings_keyboard()
    )


async def handle_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    user_id = update.effective_user.id
    user_prefs = await prefs.get(user_id)
    await query.edit_message_text(
        _settings_text(user_prefs), parse_mode="Markdown", reply_markup=_settings_keyboard()
    )


async def handle_setfmt_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    user_id = update.effective_user.id
    user_prefs = await prefs.get(user_id)
    current_fmt = user_prefs.get("format", "epub")

    buttons = []
    for fmt in ["epub", "pdf", "mobi", "azw3"]:
        if fmt in config.allowed_formats:
            marker = "* " if fmt == current_fmt else ""
            buttons.append([InlineKeyboardButton(f"{marker}{fmt.upper()}", callback_data=f"setfmt_{fmt}")])

    buttons.append([InlineKeyboardButton("Retour", callback_data="open_settings")])
    keyboard = InlineKeyboardMarkup(buttons)

    await query.edit_message_text("Quel format preferes-tu ?", reply_markup=keyboard)


async def handle_setfmt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    m = re.match(r"^setfmt_(\w+)$", query.data or "")
    if not m:
        return

    fmt = m.group(1)
    user_id = update.effective_user.id
    await prefs.set(user_id, "format", fmt)

    await query.edit_message_text(f"Format defini a *{fmt.upper()}*", parse_mode="Markdown")
    await asyncio.sleep(1)
    await handle_settings(update, context)


async def handle_setemail_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    _state(context).waiting_for = "email"
    await query.edit_message_text("Envoie-moi ton adresse email :")


async def handle_setkindl_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    _state(context).waiting_for = "kindle_email"
    await query.edit_message_text(
        "Envoie-moi ton adresse Kindle :\n\n"
        "*Note :* Les vieux Kindle ne supportent pas EPUB.\n"
        "Utilise *MOBI* ou *AZW3* pour une meilleure compatibilite.",
        parse_mode="Markdown"
    )


async def handle_prefs_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Oui, supprimer", callback_data="prefs_delete_execute")],
        [InlineKeyboardButton("Non, annuler", callback_data="open_settings")],
    ])

    await query.edit_message_text(
        "Ceci supprimera toutes tes preferences (format, emails). Continuer ?",
        reply_markup=keyboard,
    )


async def handle_prefs_delete_execute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    user_id = update.effective_user.id
    await prefs.delete_user(user_id)
    _state(context).waiting_for = ""

    await query.edit_message_text("Preferences supprimees. Reutilise /settings pour les reconfigurer.")
