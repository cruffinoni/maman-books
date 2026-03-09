"""SMTP email sending (generic email + Send to Kindle)."""

import asyncio
import logging
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import SmtpConfig
from exceptions import MailError

logger = logging.getLogger(__name__)


def _send_sync(file_path: str, filename: str, recipient_email: str, subject: str, smtp: SmtpConfig) -> None:
    if not smtp.is_configured():
        raise MailError("SMTP not configured (SMTP_USER and SMTP_PASSWORD required)")

    with open(file_path, "rb") as f:
        file_data = f.read()

    msg = MIMEMultipart()
    msg["From"] = smtp.sender
    msg["To"] = recipient_email
    msg["Subject"] = subject or filename

    body = MIMEText("Sent by maman-books bot", "plain")
    msg.attach(body)

    attachment = MIMEApplication(file_data, name=filename)
    attachment.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(attachment)

    try:
        with smtplib.SMTP(smtp.host, smtp.port, timeout=30) as server:
            server.starttls()
            server.login(smtp.user, smtp.password)
            server.send_message(msg)
    except Exception as e:
        raise MailError(f"SMTP error: {e}") from e

    logger.info(f"Email sent to {recipient_email}: {filename}")


async def send_file(file_path: str, filename: str, recipient_email: str, kindle: bool, smtp: SmtpConfig) -> None:
    """Send a file via email (async wrapper around blocking send)."""
    subject = "convert" if kindle else ""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _send_sync, file_path, filename, recipient_email, subject, smtp)
