from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from telegram import Update

STRINGS: dict[str, dict[str, str]] = {
    "fr": {
        "error.internal": "Une erreur interne s'est produite. Reessaie.",
        "search.empty_address": "Adresse vide. Essaie a nouveau.",
        "search.invalid_email": "Adresse email invalide. Essaie a nouveau.",
        "search.email_saved": "Email configure : `{email}`",
        "search.kindle_saved": "Adresse Kindle configuree : `{email}`\n\nPrefere *MOBI* ou *AZW3* pour envoyer vers Kindle.",
        "search.rate_limit": "Attends {seconds} secondes entre deux recherches.",
        "search.query_too_long": "Requete trop longue (max {max_len} caracteres).",
        "search.in_progress": "Recherche en cours...",
        "search.no_results": "Aucun resultat trouve pour \u00ab {query} \u00bb.\nEssaie un autre titre ou orthographe.",
        "search.non_epub_btn": "Oui, envoie-moi en {ext}",
        "search.cancel_btn": "Non, annuler",
        "search.non_epub_prompt": "Pas d'epub disponible pour \u00ab {query} \u00bb.\nJ'ai trouve {count} resultat(s) en {ext}. Ca ira ?",
        "search.expired": "Resultat expire, refais une recherche.",
        "search.choose_result": "Choisis un resultat :",
        "search.cancelled": "Recherche annulee. Envoie un nouveau titre quand tu veux !",
        "search.results_one": "1 resultat trouve :",
        "search.results_many": "{count} resultats trouves :",
        "dl.cancel_btn": "Annuler",
        "dl.expired": "Resultat expire, refais une recherche.",
        "dl.choose_format": "\u00ab {title} \u00bb\nQuel format veux-tu ?",
        "dl.choose_dest": "\u00ab {title} \u00bb\n\nOu envoyer ?",
        "dl.preparing": "Preparation...",
        "dl.searching_file": "Recherche du fichier",
        "dl.auto_retry": "Essai du resultat suivant : \u00ab {title} \u00bb...",
        "dl.torrent_waiting": "Envoi vers le client torrent pour \u00ab {title} \u00bb...\nSurveillance du dossier de telechargement...",
        "dl.progress_with_total": "Telechargement \u00ab {title} \u00bb\n{bar} {pct}%  ({downloaded} / {total})",
        "dl.progress_no_total": "Telechargement \u00ab {title} \u00bb\n{downloaded} telecharges...",
        "dl.torrent_still_waiting": "Toujours en attente pour \u00ab {title} \u00bb...\nMerci de patienter.",
        "dl.all_mirrors_failed": "Toutes les sources de telechargement sont indisponibles pour l'instant.\nReessaie dans quelques minutes ou essaie un autre titre.",
        "dl.no_result_in_size": "Aucun resultat disponible dans la limite de taille.\nRefais une recherche.",
        "dl.converting": "Conversion en {fmt} de \u00ab {title} \u00bb...",
        "dl.conversion_failed": "Conversion {fmt} echouee, envoi en EPUB a la place.",
        "dl.vt_scanning": "Analyse antivirus de \u00ab {title} \u00bb",
        "dl.vt_unavailable": "\nAnalyse VirusTotal indisponible",
        "dl.vt_blocked": "Fichier bloque \u2014 detecte comme malveillant par {count} scanner(s) VirusTotal.",
        "dl.vt_suspicious": "\nSignale comme suspect par {count} scanner(s) VirusTotal",
        "dl.sending": "Envoi de \u00ab {title} \u00bb...",
        "dl.sent_ok": "Envoye ! Bonne lecture",
        "dl.email_not_configured": "Adresse email non configuree. Utilise /settings",
        "dl.email_sending": "Envoi par email a {addr}...",
        "dl.email_sent": "Email envoye a {addr}",
        "dl.email_failed": "Envoi email echoue. Verifie la configuration SMTP dans /settings.",
        "dl.kindle_not_configured": "Adresse Kindle non configuree. Utilise /settings",
        "dl.kindle_sending": "Envoi vers Kindle ({addr})...",
        "dl.kindle_sent": "Envoye vers votre Kindle !",
        "dl.kindle_failed": "Envoi Kindle echoue. Verifie l'adresse Kindle et la config SMTP dans /settings.",
        "dl.download_cancelled": "Telechargement annule.",
        "dl.no_active_download": "Aucun telechargement en cours.",
        "onb.settings_btn": "Configurer mes preferences",
        "onb.welcome": "Bonjour ! Envoie-moi le titre d'un livre et je le chercherai pour toi.\n\nJe cherche sur Anna's Archive et Prowlarr. Tu pourras ensuite choisir le resultat a telecharger.",
        "onb.format_prompt": "Bienvenue ! Commen\u00e7ons par configurer tes preferences.\n\nQuel format preferes-tu ?",
        "onb.email_prompt": "Veux-tu configurer un email pour recevoir les livres ?\n\nEnvoie ton adresse email (ou clique Passer pour continuer).",
        "onb.skip_btn": "Passer",
        "onb.kindle_prompt": "Veux-tu configurer une adresse Kindle ?\n\nEnvoie ton adresse Kindle (ou clique Passer).\n\nLes vieux Kindle ne supportent pas EPUB.\nUtilise MOBI ou AZW3 pour une meilleure compatibilite.",
        "onb.summary": "*Configuration terminee !*\n\n\u2022 Format : `{fmt}`\n\u2022 Email : `{email}`\n\u2022 Kindle : `{kindle}`\n\nTu peux maintenant chercher des livres ! Utilise `/settings` pour modifier tes preferences a tout moment.",
        "onb.not_configured": "non configure",
        "onb.format_set": "Format defini a *{fmt}*",
        "onb.email_skipped": "Email ignore.",
        "onb.kindle_skipped": "Kindle ignore.",
        "settings.title": "*Vos preferences :*\n\n\u2022 Format par defaut : `{fmt}`\n\u2022 Email personnel : `{email}`\n\u2022 Adresse Kindle : `{kindle}`\n\u2022 Langue : `{lang}`",
        "settings.not_configured": "non configure",
        "settings.btn_format": "Format",
        "settings.btn_email": "Mon email",
        "settings.btn_kindle": "Mon Kindle",
        "settings.btn_delete": "Supprimer mes donnees",
        "settings.btn_back": "Retour",
        "settings.btn_lang": "Langue",
        "settings.format_prompt": "Quel format preferes-tu ?",
        "settings.format_set": "Format defini a *{fmt}*",
        "settings.email_prompt": "Envoie-moi ton adresse email :",
        "settings.kindle_prompt": "Envoie-moi ton adresse Kindle :\n\n*Note :* Les vieux Kindle ne supportent pas EPUB.\nUtilise *MOBI* ou *AZW3* pour une meilleure compatibilite.",
        "settings.delete_confirm": "Ceci supprimera toutes tes preferences (format, emails). Continuer ?",
        "settings.btn_delete_yes": "Oui, supprimer",
        "settings.btn_delete_no": "Non, annuler",
        "settings.deleted": "Preferences supprimees. Reutilise /settings pour les reconfigurer.",
        "settings.lang_prompt": "Quelle langue preferes-tu ?",
        "settings.lang_set_fr": "Langue definie : Francais",
        "settings.lang_set_en": "Langue definie : Anglais",
        "onb.lang_prompt": "Quelle langue preferes-tu ? / Which language do you prefer?",
        "onb.lang_set": "Langue definie : Francais",
        "fmt.kb": "Ko",
        "fmt.mb": "Mo",
    },
    "en": {
        "error.internal": "An internal error occurred. Please try again.",
        "search.empty_address": "Empty address. Please try again.",
        "search.invalid_email": "Invalid email address. Please try again.",
        "search.email_saved": "Email saved: `{email}`",
        "search.kindle_saved": "Kindle address saved: `{email}`\n\nPrefer *MOBI* or *AZW3* to send to Kindle.",
        "search.rate_limit": "Please wait {seconds} seconds between searches.",
        "search.query_too_long": "Query too long (max {max_len} characters).",
        "search.in_progress": "Searching...",
        "search.no_results": "No results found for \u00ab {query} \u00bb.\nTry a different title or spelling.",
        "search.non_epub_btn": "Yes, send me in {ext}",
        "search.cancel_btn": "No, cancel",
        "search.non_epub_prompt": "No epub available for \u00ab {query} \u00bb.\nFound {count} result(s) in {ext}. Is that OK?",
        "search.expired": "Results expired, please search again.",
        "search.choose_result": "Choose a result:",
        "search.cancelled": "Search cancelled. Send a new title whenever you're ready!",
        "search.results_one": "1 result found:",
        "search.results_many": "{count} results found:",
        "dl.cancel_btn": "Cancel",
        "dl.expired": "Results expired, please search again.",
        "dl.choose_format": "\u00ab {title} \u00bb\nWhich format do you want?",
        "dl.choose_dest": "\u00ab {title} \u00bb\n\nWhere to send it?",
        "dl.preparing": "Preparing...",
        "dl.searching_file": "Looking for file",
        "dl.auto_retry": "Trying next result: \u00ab {title} \u00bb...",
        "dl.torrent_waiting": "Sending to torrent client for \u00ab {title} \u00bb...\nWatching download folder...",
        "dl.progress_with_total": "Downloading \u00ab {title} \u00bb\n{bar} {pct}%  ({downloaded} / {total})",
        "dl.progress_no_total": "Downloading \u00ab {title} \u00bb\n{downloaded} downloaded...",
        "dl.torrent_still_waiting": "Still waiting for \u00ab {title} \u00bb...\nPlease be patient.",
        "dl.all_mirrors_failed": "All download sources are currently unavailable.\nTry again in a few minutes or try another title.",
        "dl.no_result_in_size": "No result available within the size limit.\nPlease search again.",
        "dl.converting": "Converting \u00ab {title} \u00bb to {fmt}...",
        "dl.conversion_failed": "Conversion to {fmt} failed, sending as EPUB instead.",
        "dl.vt_scanning": "Antivirus scan of \u00ab {title} \u00bb",
        "dl.vt_unavailable": "\nVirusTotal scan unavailable",
        "dl.vt_blocked": "File blocked \u2014 detected as malicious by {count} VirusTotal scanner(s).",
        "dl.vt_suspicious": "\nFlagged as suspicious by {count} VirusTotal scanner(s)",
        "dl.sending": "Sending \u00ab {title} \u00bb...",
        "dl.sent_ok": "Sent! Enjoy your book.",
        "dl.email_not_configured": "Email address not configured. Use /settings",
        "dl.email_sending": "Sending by email to {addr}...",
        "dl.email_sent": "Email sent to {addr}",
        "dl.email_failed": "Email sending failed. Check SMTP configuration in /settings.",
        "dl.kindle_not_configured": "Kindle address not configured. Use /settings",
        "dl.kindle_sending": "Sending to Kindle ({addr})...",
        "dl.kindle_sent": "Sent to your Kindle!",
        "dl.kindle_failed": "Kindle sending failed. Check Kindle address and SMTP config in /settings.",
        "dl.download_cancelled": "Download cancelled.",
        "dl.no_active_download": "No download in progress.",
        "onb.settings_btn": "Configure my preferences",
        "onb.welcome": "Hello! Send me a book title and I'll search for it.\n\nI search Anna's Archive and Prowlarr. You can then choose which result to download.",
        "onb.format_prompt": "Welcome! Let's start by setting up your preferences.\n\nWhich format do you prefer?",
        "onb.email_prompt": "Would you like to configure an email to receive books?\n\nSend your email address (or click Skip to continue).",
        "onb.skip_btn": "Skip",
        "onb.kindle_prompt": "Would you like to configure a Kindle address?\n\nSend your Kindle address (or click Skip).\n\nOld Kindles do not support EPUB.\nUse MOBI or AZW3 for better compatibility.",
        "onb.summary": "*Setup complete!*\n\n\u2022 Format: `{fmt}`\n\u2022 Email: `{email}`\n\u2022 Kindle: `{kindle}`\n\nYou can now search for books! Use `/settings` to change your preferences at any time.",
        "onb.not_configured": "not configured",
        "onb.format_set": "Format set to *{fmt}*",
        "onb.email_skipped": "Email skipped.",
        "onb.kindle_skipped": "Kindle skipped.",
        "settings.title": "*Your preferences:*\n\n\u2022 Default format: `{fmt}`\n\u2022 Personal email: `{email}`\n\u2022 Kindle address: `{kindle}`\n\u2022 Language: `{lang}`",
        "settings.not_configured": "not configured",
        "settings.btn_format": "Format",
        "settings.btn_email": "My email",
        "settings.btn_kindle": "My Kindle",
        "settings.btn_delete": "Delete my data",
        "settings.btn_back": "Back",
        "settings.btn_lang": "Language",
        "settings.format_prompt": "Which format do you prefer?",
        "settings.format_set": "Format set to *{fmt}*",
        "settings.email_prompt": "Send me your email address:",
        "settings.kindle_prompt": "Send me your Kindle address:\n\n*Note:* Old Kindles do not support EPUB.\nUse *MOBI* or *AZW3* for better compatibility.",
        "settings.delete_confirm": "This will delete all your preferences (format, emails). Continue?",
        "settings.btn_delete_yes": "Yes, delete",
        "settings.btn_delete_no": "No, cancel",
        "settings.deleted": "Preferences deleted. Use /settings to reconfigure them.",
        "settings.lang_prompt": "Which language do you prefer?",
        "settings.lang_set_fr": "Language set: French",
        "settings.lang_set_en": "Language set: English",
        "onb.lang_prompt": "Quelle langue preferes-tu ? / Which language do you prefer?",
        "onb.lang_set": "Language set: English",
        "fmt.kb": "KB",
        "fmt.mb": "MB",
    },
}


def get_lang(update: "Update | None", user_prefs: dict | None = None) -> str:
    """Return the user's preferred language ('fr' or 'en').

    Priority: persisted pref in user_prefs > Telegram locale > 'fr' default.
    """
    if user_prefs is not None:
        stored = user_prefs.get("lang")
        if stored in ("fr", "en"):
            return stored
    if update is None:
        return "fr"
    user = update.effective_user
    if user is None:
        return "fr"
    code = user.language_code
    if code and code.startswith("en"):
        return "en"
    return "fr"


def t(key: str, lang: str, **kwargs: str) -> str:
    """Look up a translated string, falling back to 'fr', then to the key itself."""
    lang_strings = STRINGS.get(lang, {})
    text = lang_strings.get(key)
    if text is None:
        text = STRINGS.get("fr", {}).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text
