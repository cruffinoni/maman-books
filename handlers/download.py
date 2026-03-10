import asyncio
import logging
import os
import re
import tempfile

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import prefs
from config import Config
from exceptions import AllMirrorsFailedError, FileTooLargeError, DownloadError, MailError, VirusTotalError
from handlers._common import _is_allowed, _state, _fmt_size
from i18n import get_lang, t
from models import SearchResult
from services import converter, downloader, mailer, virustotal

logger = logging.getLogger(__name__)


def _cancel_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(t("dl.cancel_btn", lang), callback_data="cancel_dl")]])


def _progress_bar(pct: int) -> str:
    filled = pct // 10
    return ">" * filled + "-" * (10 - filled)


async def _animate_preparing(query, title: str, started: asyncio.Event, lang: str, reply_markup=None) -> None:
    """Show animated dots until streaming starts or task is cancelled."""
    base = t("dl.searching_file", lang)
    frames = [f"{base} .", f"{base} ..", f"{base} ..."]
    i = 0
    try:
        while not started.is_set():
            try:
                await query.edit_message_text(frames[i % len(frames)], reply_markup=reply_markup)
            except Exception:
                pass
            i += 1
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass


async def handle_download(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    lang = get_lang(update)
    data = query.data or ""
    if not data.startswith("dl_"):
        return

    try:
        idx = int(data[3:])
    except ValueError:
        return

    st = _state(context)
    results = st.results
    if idx >= len(results):
        await query.edit_message_text(t("dl.expired", lang))
        return

    result = results[idx]
    available_formats = {result.ext}
    if len(config.allowed_formats) > 1 and available_formats & set(config.allowed_formats):
        title = result.title or "ce livre"
        fmt_buttons = [
            InlineKeyboardButton("EPUB", callback_data=f"dlfmt_epub_{idx}") if "epub" in config.allowed_formats else None,
            InlineKeyboardButton("PDF", callback_data=f"dlfmt_pdf_{idx}") if "pdf" in config.allowed_formats else None,
            InlineKeyboardButton("MOBI", callback_data=f"dlfmt_mobi_{idx}") if "mobi" in config.allowed_formats else None,
            InlineKeyboardButton("AZW3", callback_data=f"dlfmt_azw3_{idx}") if "azw3" in config.allowed_formats else None,
        ]
        keyboard = InlineKeyboardMarkup([
            [b for b in fmt_buttons if b],
            [InlineKeyboardButton(t("dl.cancel_btn", lang), callback_data="cancel_dl")],
        ])
        await query.edit_message_text(
            t("dl.choose_format", lang, title=title[:60]),
            reply_markup=keyboard,
        )
        return

    desired_fmt = config.allowed_formats[0] if config.allowed_formats else "epub"
    st.pending_format[idx] = desired_fmt

    user_prefs = await prefs.get(update.effective_user.id)
    has_email = bool(user_prefs.get("email"))
    has_kindle = bool(user_prefs.get("kindle_email"))

    if has_email or has_kindle:
        title = result.title or "ce livre"
        dest_buttons = [InlineKeyboardButton("Telegram", callback_data=f"dest_telegram_{idx}")]
        if has_email:
            dest_buttons.append(InlineKeyboardButton("Email", callback_data=f"dest_email_{idx}"))
        if has_kindle:
            dest_buttons.append(InlineKeyboardButton("Kindle", callback_data=f"dest_kindle_{idx}"))

        keyboard = InlineKeyboardMarkup([
            dest_buttons,
            [InlineKeyboardButton(t("dl.cancel_btn", lang), callback_data="cancel_dl")],
        ])
        await query.edit_message_text(
            t("dl.choose_dest", lang, title=title[:50]),
            reply_markup=keyboard,
        )
    else:
        await _do_download(query, context, idx, desired_fmt=desired_fmt, destination="telegram", lang=lang)


async def handle_download_fmt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    lang = get_lang(update)
    m = re.match(r"^dlfmt_(epub|pdf|mobi|azw3)_(\d+)$", query.data or "")
    if not m:
        return

    fmt, idx = m.group(1), int(m.group(2))

    st = _state(context)
    results = st.results
    if idx >= len(results):
        await query.edit_message_text(t("dl.expired", lang))
        return

    user_prefs = await prefs.get(update.effective_user.id)
    has_email = bool(user_prefs.get("email"))
    has_kindle = bool(user_prefs.get("kindle_email"))

    st.pending_format[idx] = fmt

    if has_email or has_kindle:
        result = results[idx]
        title = result.title or "ce livre"
        dest_buttons = [InlineKeyboardButton("Telegram", callback_data=f"dest_telegram_{idx}")]
        if has_email:
            dest_buttons.append(InlineKeyboardButton("Email", callback_data=f"dest_email_{idx}"))
        if has_kindle:
            dest_buttons.append(InlineKeyboardButton("Kindle", callback_data=f"dest_kindle_{idx}"))

        keyboard = InlineKeyboardMarkup([
            dest_buttons,
            [InlineKeyboardButton(t("dl.cancel_btn", lang), callback_data="cancel_dl")],
        ])
        await query.edit_message_text(
            t("dl.choose_dest", lang, title=title[:50]),
            reply_markup=keyboard,
        )
    else:
        await _do_download(query, context, idx, desired_fmt=fmt, destination="telegram", lang=lang)


async def handle_dest_telegram(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    lang = get_lang(update)
    m = re.match(r"^dest_telegram_(\d+)$", query.data or "")
    if not m:
        return

    idx = int(m.group(1))
    fmt = _state(context).pending_format.get(idx, "epub")
    await _do_download(query, context, idx, desired_fmt=fmt, destination="telegram", lang=lang)


async def handle_dest_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    lang = get_lang(update)
    m = re.match(r"^dest_email_(\d+)$", query.data or "")
    if not m:
        return

    idx = int(m.group(1))
    fmt = _state(context).pending_format.get(idx, "epub")
    await _do_download(query, context, idx, desired_fmt=fmt, destination="email", lang=lang)


async def handle_dest_kindle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    lang = get_lang(update)
    m = re.match(r"^dest_kindle_(\d+)$", query.data or "")
    if not m:
        return

    idx = int(m.group(1))
    fmt = _state(context).pending_format.get(idx, "epub")
    await _do_download(query, context, idx, desired_fmt=fmt, destination="kindle", lang=lang)


async def _do_download(query, context: ContextTypes.DEFAULT_TYPE, idx: int, desired_fmt: str = "epub", destination: str = "telegram", lang: str = "fr") -> None:
    config: Config = context.bot_data["config"]
    st = _state(context)
    results = st.results
    if idx >= len(results):
        await query.edit_message_text(t("dl.expired", lang))
        return

    cancel_kb = _cancel_kb(lang)

    async def _try_download(start_idx: int) -> tuple[str, SearchResult] | None | str:
        """Try results from start_idx onwards, return (file_path, result), None, or 'mirrors'."""
        any_mirror_failure = False
        for i in range(start_idx, len(results)):
            result = results[i]
            title = result.title or "livre"
            ext = result.ext or "epub"
            is_torrent = result.is_torrent

            if desired_fmt in ("mobi", "azw3", "pdf") and ext not in ("epub", "pdf"):
                continue

            if i > start_idx:
                logger.info(f"Auto-retry on result {i}: {title!r}")
                await query.edit_message_text(t("dl.auto_retry", lang, title=title), reply_markup=cancel_kb)

            if is_torrent:
                await query.edit_message_text(
                    t("dl.torrent_waiting", lang, title=title),
                    reply_markup=cancel_kb,
                )
            else:
                await query.edit_message_text(t("dl.preparing", lang), reply_markup=cancel_kb)

            streaming_started = asyncio.Event()
            dots_task = asyncio.create_task(_animate_preparing(query, title, streaming_started, lang, reply_markup=cancel_kb))

            async def on_progress(downloaded: int, total: int, _title=title) -> None:
                if not streaming_started.is_set():
                    streaming_started.set()
                if total:
                    pct = min(int(downloaded / total * 100), 99)
                    bar = _progress_bar(pct)
                    await query.edit_message_text(
                        t("dl.progress_with_total", lang, title=_title, bar=bar, pct=pct,
                          downloaded=_fmt_size(downloaded, lang), total=_fmt_size(total, lang)),
                        reply_markup=cancel_kb,
                    )
                else:
                    await query.edit_message_text(
                        t("dl.progress_no_total", lang, title=_title, downloaded=_fmt_size(downloaded, lang)),
                        reply_markup=cancel_kb,
                    )

            dl_task = asyncio.create_task(
                downloader.download_result(result, progress_callback=None if is_torrent else on_progress, max_bytes=config.max_file_size, config=config)
            )
            if is_torrent:
                while not dl_task.done():
                    await asyncio.sleep(30)
                    if not dl_task.done():
                        try:
                            await query.edit_message_text(
                                t("dl.torrent_still_waiting", lang, title=title),
                                reply_markup=cancel_kb,
                            )
                        except Exception:
                            pass

            try:
                file_path = await dl_task
            except asyncio.CancelledError:
                dl_task.cancel()
                raise
            except (AllMirrorsFailedError, FileTooLargeError, DownloadError, TimeoutError) as e:
                logger.warning(f"Result {i} failed ({e}), skipping")
                dots_task.cancel()
                any_mirror_failure = True
                continue
            except Exception as e:
                logger.warning(f"Result {i} failed ({e}), skipping")
                dots_task.cancel()
                any_mirror_failure = True
                continue
            finally:
                dots_task.cancel()

            size = os.path.getsize(file_path)
            if size > config.max_file_size:
                logger.info(f"Result {i} too large ({_fmt_size(size)}), skipping")
                try:
                    os.remove(file_path)
                except Exception:
                    pass
                continue

            return file_path, result

        return "mirrors" if any_mirror_failure else None

    download_task = asyncio.create_task(_try_download(idx))
    st.active_dl_task = download_task
    try:
        while not download_task.done():
            try:
                await asyncio.wait_for(asyncio.shield(download_task), timeout=0.5)
            except asyncio.TimeoutError:
                continue
        outcome = download_task.result()
    except asyncio.CancelledError:
        return
    finally:
        st.active_dl_task = None

    if outcome is None or isinstance(outcome, str):
        if outcome == "mirrors":
            msg_text = t("dl.all_mirrors_failed", lang)
        else:
            msg_text = t("dl.no_result_in_size", lang)
        await query.edit_message_text(msg_text)
        return

    file_path, result = outcome
    title = result.title or "livre"
    ext = result.ext or "epub"

    send_path = file_path
    send_ext = ext
    converted_path = None

    if ext == "epub" and desired_fmt != "epub":
        try:
            if desired_fmt == "pdf":
                await query.edit_message_text(t("dl.converting", lang, fmt="PDF", title=title[:50]))
                converted_path = await converter.epub_to_pdf(file_path)
                send_ext = "pdf"
            elif desired_fmt == "mobi":
                await query.edit_message_text(t("dl.converting", lang, fmt="MOBI", title=title[:50]))
                converted_path = await converter.epub_to_mobi(file_path)
                send_ext = "mobi"
            elif desired_fmt == "azw3":
                await query.edit_message_text(t("dl.converting", lang, fmt="AZW3", title=title[:50]))
                converted_path = await converter.epub_to_azw3(file_path)
                send_ext = "azw3"

            if converted_path:
                send_path = converted_path
        except Exception as e:
            logger.warning(f"Conversion to {desired_fmt} failed: {e}")
            await query.edit_message_text(t("dl.conversion_failed", lang, fmt=desired_fmt.upper()))
            send_path = file_path
            send_ext = ext

    try:
        vt_caption = ""
        if config.virustotal_api_key:
            try:
                vt_base = t("dl.vt_scanning", lang, title=title[:45])
                _vt_frames = [f"{vt_base} .", f"{vt_base} ..", f"{vt_base} ..."]

                async def _animate_vt():
                    i = 0
                    try:
                        while True:
                            try:
                                await query.edit_message_text(_vt_frames[i % len(_vt_frames)])
                            except Exception:
                                pass
                            i += 1
                            await asyncio.sleep(1)
                    except asyncio.CancelledError:
                        pass

                vt_anim = asyncio.create_task(_animate_vt())
                try:
                    stats = await virustotal.scan_file(send_path, config.virustotal_api_key)
                except VirusTotalError as e:
                    logger.warning(f"VirusTotal scan failed: {e}")
                    stats = None
                    vt_caption = t("dl.vt_unavailable", lang)
                finally:
                    vt_anim.cancel()
                if stats:
                    malicious = stats.get("malicious", 0)
                    suspicious = stats.get("suspicious", 0)
                    if malicious > 0:
                        await query.edit_message_text(t("dl.vt_blocked", lang, count=malicious))
                        return
                    elif suspicious > 0:
                        vt_caption = t("dl.vt_suspicious", lang, count=suspicious)
            except Exception as e:
                logger.warning(f"VirusTotal scan failed: {e}")
                vt_caption = t("dl.vt_unavailable", lang)

        safe_title = re.sub(r'[^\w\s\-]', '', title).strip()[:60] or "livre"
        filename = f"{safe_title}.{send_ext}"

        if destination == "telegram":
            await query.edit_message_text(t("dl.sending", lang, title=title))
            with open(send_path, "rb") as f:
                await query.message.reply_document(
                    document=f,
                    filename=filename,
                    caption=f"{title}{vt_caption}",
                )
            await query.edit_message_text(t("dl.sent_ok", lang))

        elif destination == "email":
            user_id = query.from_user.id
            user_prefs = await prefs.get(user_id)
            email_addr = user_prefs.get("email")
            if not email_addr:
                await query.edit_message_text(t("dl.email_not_configured", lang))
                return
            try:
                await query.edit_message_text(t("dl.email_sending", lang, addr=email_addr))
                await mailer.send_file(send_path, filename, email_addr, kindle=False, smtp=config.smtp)
                await query.edit_message_text(t("dl.email_sent", lang, addr=email_addr))
            except MailError as e:
                logger.warning(f"Email send failed: {e}")
                await query.edit_message_text(t("dl.email_failed", lang))

        elif destination == "kindle":
            user_id = query.from_user.id
            user_prefs = await prefs.get(user_id)
            kindle_email = user_prefs.get("kindle_email")
            if not kindle_email:
                await query.edit_message_text(t("dl.kindle_not_configured", lang))
                return
            try:
                await query.edit_message_text(t("dl.kindle_sending", lang, addr=kindle_email))
                await mailer.send_file(send_path, filename, kindle_email, kindle=True, smtp=config.smtp)
                await query.edit_message_text(t("dl.kindle_sent", lang))
            except MailError as e:
                logger.warning(f"Kindle send failed: {e}")
                await query.edit_message_text(t("dl.kindle_failed", lang))
    finally:
        for path in (file_path, converted_path):
            if path and path.startswith(tempfile.gettempdir()):
                try:
                    os.remove(path)
                except Exception:
                    pass


async def handle_cancel_download(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config: Config = context.bot_data["config"]
    if not _is_allowed(update, config):
        return

    lang = get_lang(update)
    st = _state(context)
    task = st.active_dl_task
    st.active_dl_task = None
    if task and not task.done():
        task.cancel()
        await query.edit_message_text(t("dl.download_cancelled", lang))
    else:
        await query.edit_message_text(t("dl.no_active_download", lang))
