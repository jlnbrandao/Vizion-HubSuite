"""Email delivery for invitations and password resets."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from src.config.settings import Settings

logger = logging.getLogger("vizion.mail")


class EmailSender:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send(self, *, to: str, subject: str, body: str) -> None:
        if not self._settings.smtp_host:
            logger.info("MAIL (dev stub) to=%s subject=%s\n%s", to, subject, body)
            return
        msg = EmailMessage()
        msg["From"] = self._settings.smtp_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        with smtplib.SMTP(self._settings.smtp_host, self._settings.smtp_port) as smtp:
            if self._settings.smtp_use_tls:
                smtp.starttls()
            if self._settings.smtp_username:
                smtp.login(self._settings.smtp_username, self._settings.smtp_password)
            smtp.send_message(msg)
