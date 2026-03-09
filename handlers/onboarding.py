import asyncio
import logging
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import prefs
from config import Config
from handlers._common import _is_allowed, _state

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    user_id = update.effective_user.id
    user_prefs = await prefs.get(user_id)

    if not user_prefs:
        _state(context).onboarding_step = "format"
        await handle_onboarding_format(update, context)
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Configurer mes preferences", callback_data="open_settings")],
    ])
    await update.message.reply_text(
        "Bonjour ! Envoie-moi le titre d'un livre et je le chercherai pour toi.\n\n"
        "Je cherche sur Anna's Archive et Prowlarr. "
        "Tu pourras ensuite choisir le resultat a telecharger.",
        reply_markup=keyboard,
    )


async def handle_onboarding_format(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """First step of onboarding: choose format."""
    config: Config = context.bot_data["config"]
    _state(context).onboarding_step = "format"

    buttons = []
    for fmt in ["epub", "pdf", "mobi", "azw3"]:
        if fmt in config.allowed_formats:
            buttons.append([InlineKeyboardButton(f"{fmt.upper()}", callback_data=f"onb_fmt_{fmt}")])

    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        "Bienvenue ! Commençons par configurer tes preferences.\n\n"
        "Quel format preferes-tu ?",
        reply_markup=keyboard,
    )


async def handle_onboarding_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Second step of onboarding: ask for email."""
    query = update.callback_query
    await query.answer()

    st = _state(context)
    st.onboarding_step = "email"
    st.waiting_for = "onb_email"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Passer", callback_data="onb_skip_email")],
    ])
    await query.edit_message_text(
        "Veux-tu configurer un email pour recevoir les livres ?\n\n"
        "Envoie ton adresse email (ou clique Passer pour continuer).",
        reply_markup=keyboard,
    )


async def handle_onboarding_kindle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Third step of onboarding: ask for Kindle email."""
    if update.callback_query:
        await update.callback_query.answer()

    st = _state(context)
    st.onboarding_step = "kindle"
    st.waiting_for = "onb_kindle"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Passer", callback_data="onb_skip_kindle")],
    ])

    msg_text = (
        "Veux-tu configurer une adresse Kindle ?\n\n"
        "Envoie ton adresse Kindle (ou clique Passer).\n\n"
        "Les vieux Kindle ne supportent pas EPUB.\n"
        "Utilise MOBI ou AZW3 pour une meilleure compatibilite."
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(msg_text, reply_markup=keyboard)
    else:
        await update.message.reply_text(msg_text, reply_markup=keyboard)


async def handle_onboarding_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Final step of onboarding: show summary."""
    user_id = update.effective_user.id
    user_prefs = await prefs.get(user_id)

    fmt = user_prefs.get("format", "?")
    email = user_prefs.get("email", "non configure")
    kindle = user_prefs.get("kindle_email", "non configure")

    summary_text = (
        "*Configuration terminee !*\n\n"
        f"• Format : `{fmt.upper()}`\n"
        f"• Email : `{email}`\n"
        f"• Kindle : `{kindle}`\n\n"
        "Tu peux maintenant chercher des livres ! "
        "Utilise `/settings` pour modifier tes preferences a tout moment."
    )

    st = _state(context)
    st.onboarding_step = ""
    st.waiting_for = ""

    if update.callback_query is None:
        await update.message.reply_text(summary_text, parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(summary_text, parse_mode="Markdown")


async def handle_onb_fmt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Onboarding: set format and continue to email."""
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    m = re.match(r"^onb_fmt_(\w+)$", query.data or "")
    if not m:
        return

    fmt = m.group(1)
    user_id = update.effective_user.id
    await prefs.set(user_id, "format", fmt)

    await query.edit_message_text(f"Format defini a *{fmt.upper()}*", parse_mode="Markdown")
    await asyncio.sleep(0.5)
    await handle_onboarding_email(update, context)


async def handle_onb_skip_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Onboarding: skip email and continue to Kindle."""
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    _state(context).waiting_for = ""
    await query.edit_message_text("Email ignore.")
    await asyncio.sleep(0.5)
    await handle_onboarding_kindle(update, context)


async def handle_onb_skip_kindle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Onboarding: skip Kindle and show summary."""
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    _state(context).waiting_for = ""
    await query.edit_message_text("Kindle ignore.")
    await asyncio.sleep(0.5)
    await handle_onboarding_summary(update, context)
