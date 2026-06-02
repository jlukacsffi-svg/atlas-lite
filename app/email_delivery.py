"""Optional email delivery for Atlas Lite reports."""

from email.message import EmailMessage
from pathlib import Path
import mimetypes
import os
import smtplib
import ssl


TRUE_VALUES = {"1", "true", "yes", "on"}


class EmailConfig:
    """Read email delivery settings from environment variables."""

    def __init__(self):
        self.enabled = os.getenv("ATLAS_EMAIL_ENABLED", "").strip().lower() in TRUE_VALUES
        self.smtp_host = os.getenv("ATLAS_SMTP_HOST", "").strip()
        self.smtp_port = int(os.getenv("ATLAS_SMTP_PORT", "587"))
        self.smtp_user = os.getenv("ATLAS_SMTP_USER", "").strip()
        self.smtp_password = os.getenv("ATLAS_SMTP_PASSWORD", "")
        self.sender = os.getenv("ATLAS_EMAIL_FROM", self.smtp_user).strip()
        self.recipients = self._split_addresses(os.getenv("ATLAS_EMAIL_TO", ""))
        self.use_ssl = os.getenv("ATLAS_SMTP_USE_SSL", "").strip().lower() in TRUE_VALUES
        self.use_starttls = os.getenv("ATLAS_SMTP_USE_STARTTLS", "true").strip().lower() in TRUE_VALUES

    def _split_addresses(self, raw_value):
        return [
            address.strip()
            for address in raw_value.replace(";", ",").split(",")
            if address.strip()
        ]

    def validate(self):
        missing = []
        if not self.smtp_host:
            missing.append("ATLAS_SMTP_HOST")
        if not self.smtp_user:
            missing.append("ATLAS_SMTP_USER")
        if not self.smtp_password:
            missing.append("ATLAS_SMTP_PASSWORD")
        if not self.sender:
            missing.append("ATLAS_EMAIL_FROM")
        if not self.recipients:
            missing.append("ATLAS_EMAIL_TO")

        if missing:
            raise ValueError(f"Email delivery is enabled but missing: {', '.join(missing)}")


class EmailDelivery:
    """Send Atlas reports by email when configured."""

    def __init__(self, config=None):
        self.config = config or EmailConfig()

    def send_report(self, markdown_path, html_path=None, subject=None):
        if not self.config.enabled:
            return False

        self.config.validate()

        markdown_path = Path(markdown_path)
        html_path = Path(html_path) if html_path else None
        subject = subject or f"Atlas Lite Morning Executive Brief - {markdown_path.stem}"

        message = EmailMessage()
        message["From"] = self.config.sender
        message["To"] = ", ".join(self.config.recipients)
        message["Subject"] = subject
        message.set_content(
            "Atlas Lite generated today's Morning Executive Brief.\n\n"
            "The Markdown and HTML report files are attached.\n"
        )

        for attachment_path in [markdown_path, html_path]:
            if attachment_path:
                self._attach_file(message, attachment_path)

        self._send(message)
        return True

    def _attach_file(self, message, filepath):
        mime_type, _ = mimetypes.guess_type(filepath.name)
        if mime_type:
            maintype, subtype = mime_type.split("/", 1)
        else:
            maintype, subtype = "application", "octet-stream"

        with open(filepath, "rb") as f:
            message.add_attachment(
                f.read(),
                maintype=maintype,
                subtype=subtype,
                filename=filepath.name,
            )

    def _send(self, message):
        if self.config.use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(self.config.smtp_host, self.config.smtp_port, context=context) as server:
                server.login(self.config.smtp_user, self.config.smtp_password)
                server.send_message(message)
            return

        with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
            if self.config.use_starttls:
                server.starttls(context=ssl.create_default_context())
            server.login(self.config.smtp_user, self.config.smtp_password)
            server.send_message(message)
