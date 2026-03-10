import asyncio
import logging
import re
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import prefs
from config import Config
from handlers._common import _is_allowed, _state, _fmt_size
from handlers.onboarding import handle_onboarding_kindle, handle_onboarding_summary
from models import SearchResult
from services import anna_archive, prowlarr
from services.scorer import parse_query, rank

logger = logging.getLogger(__name__)


async def _safe_search(fn, *args, source_name: str) -> list[SearchResult]:
    try:
        return await fn(*args)
    except Exception as e:
        logger.warning(f"{source_name} search error: {e}")
        return []


async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    st = _state(context)

    if st.waiting_for in ("email", "kindle_email", "onb_email", "onb_kindle"):
        user_input = update.message.text.strip()
        if not user_input:
            await update.message.reply_text("Adresse vide. Essaie a nouveau.")
            return

        if not re.match(r"[^@]+@[^@]+\.[^@]+", user_input):
            await update.message.reply_text("Adresse email invalide. Essaie a nouveau.")
            return

        user_id = update.effective_user.id

        if st.waiting_for == "onb_email":
            await prefs.set(user_id, "email", user_input)
            st.waiting_for = ""
            await update.message.reply_text(f"Email configure : `{user_input}`", parse_mode="Markdown")
            await asyncio.sleep(0.5)
            await handle_onboarding_kindle(update, context)
            return
        elif st.waiting_for == "onb_kindle":
            await prefs.set(user_id, "kindle_email", user_input)
            st.waiting_for = ""
            await update.message.reply_text(
                f"Adresse Kindle configuree : `{user_input}`\n\n"
                "Prefere *MOBI* ou *AZW3* pour envoyer vers Kindle.",
                parse_mode="Markdown"
            )
            await asyncio.sleep(0.5)
            await handle_onboarding_summary(update, context)
            return

        if st.waiting_for == "email":
            await prefs.set(user_id, "email", user_input)
            st.waiting_for = ""
            await update.message.reply_text(f"Email configure : `{user_input}`", parse_mode="Markdown")
        else:
            await prefs.set(user_id, "kindle_email", user_input)
            st.waiting_for = ""
            await update.message.reply_text(
                f"Adresse Kindle configuree : `{user_input}`\n\n"
                "Prefere *MOBI* ou *AZW3* pour envoyer vers Kindle.",
                parse_mode="Markdown"
            )
        return

    now = time.monotonic()
    if now - st.last_search_at < config.rate_limit_seconds:
        await update.message.reply_text(f"Attends {config.rate_limit_seconds} secondes entre deux recherches.")
        return
    st.last_search_at = now

    query = update.message.text.strip()
    if not query:
        return

    if len(query) > config.max_query_length:
        await update.message.reply_text(f"Requete trop longue (max {config.max_query_length} caracteres).")
        return

    msg = await update.message.reply_text("Recherche en cours...")

    aa_results, pr_results = await asyncio.gather(
        _safe_search(anna_archive.search, query, config.anna_archive_url, source_name="Anna's Archive"),
        _safe_search(prowlarr.search, query, config.prowlarr_url, config.prowlarr_api_key, source_name="Prowlarr"),
    )

    logger.info(f"=== Results for '{query}' ===")
    logger.info(f"Anna's Archive ({len(aa_results)}):")
    for r in aa_results:
        logger.info(f"  [AA] {r.title!r} — {r.ext} — {_fmt_size(r.size_bytes)} — md5={r.md5}")
    logger.info(f"Prowlarr ({len(pr_results)}):")
    for r in pr_results:
        logger.info(f"  [PR] {r.title!r} — {r.ext} — {_fmt_size(r.size_bytes)} — torrent={r.is_torrent}")

    pq = parse_query(query)
    combined = aa_results + pr_results
    scored = rank(combined, pq)
    all_results = [r for _, r in sorted(zip(scored, combined), key=lambda x: x[0], reverse=True)]
    filtered = [r for r in all_results if not (r.size_bytes > config.max_file_size)]

    seen_titles: set[str] = set()
    results: list[SearchResult] = []
    for r in filtered:
        norm = re.sub(r"[^\w]", "", (r.title or "")).lower()[:35]
        if norm and norm in seen_titles:
            continue
        if norm:
            seen_titles.add(norm)
        results.append(r)
        if len(results) >= config.max_results:
            break

    skipped = len(all_results) - len(results)
    logger.info(f"Merged total: {len(results)} result(s) ({skipped} excluded/deduplicated)")

    has_epub = any(r.ext == "epub" for r in results)
    non_epub_results = [r for r in results if r.ext != "epub"]

    if not results:
        await msg.edit_text(
            f"Aucun resultat trouve pour « {query} ».\nEssaie un autre titre ou orthographe."
        )
        return

    if not has_epub and non_epub_results:
        exts = list({r.ext for r in non_epub_results if r.ext})
        ext_str = ", ".join(exts).upper()
        st.results = results
        st.pending_non_epub = True
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"Oui, envoie-moi en {ext_str}", callback_data="confirm_non_epub")],
            [InlineKeyboardButton("Non, annuler", callback_data="cancel_search")],
        ])
        await msg.edit_text(
            f"Pas d'epub disponible pour « {query} ».\n"
            f"J'ai trouve {len(results)} resultat(s) en {ext_str}. Ca ira ?",
            reply_markup=keyboard,
        )
        return

    st.results = results

    buttons = []
    for i, r in enumerate(results):
        if r.ext != "epub" and has_epub:
            continue
        icon = "direct" if not r.is_torrent else "torrent"
        title_short = r.title[:45] + "..." if len(r.title) > 45 else r.title
        label = f"[{icon}] {title_short}"
        if r.author:
            label += f" - {r.author[:20]}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"dl_{i}")])

    keyboard = InlineKeyboardMarkup(buttons)
    n = len(buttons)
    await msg.edit_text(
        f"{n} resultat{'s' if n > 1 else ''} trouve{'s' if n > 1 else ''} :",
        reply_markup=keyboard,
    )


async def handle_confirm_non_epub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    st = _state(context)
    results = st.results
    if not results:
        await query.edit_message_text("Resultat expire, refais une recherche.")
        return

    buttons = []
    for i, r in enumerate(results):
        icon = "direct" if not r.is_torrent else "torrent"
        title_short = (r.title or "?")[:40]
        ext = r.ext or "?"
        size = _fmt_size(r.size_bytes)
        buttons.append([InlineKeyboardButton(f"[{icon}] {title_short} — {ext} — {size}", callback_data=f"dl_{i}")])
    await query.edit_message_text(
        "Choisis un resultat :",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def handle_cancel_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _state(context).results = []
    await query.edit_message_text("Recherche annulee. Envoie un nouveau titre quand tu veux !")
