import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Send an email using SMTP settings from config.
    Returns True on success, False on failure.
    Requires SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_EMAIL to be configured in .env.
    """
    if not settings.SMTP_SERVER or not settings.SMTP_USERNAME:
        logger.warning(
            "Email not configured: SMTP_SERVER or SMTP_USERNAME is empty. Skipping send."
        )
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False
