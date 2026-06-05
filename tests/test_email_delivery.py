import tempfile
import unittest
from pathlib import Path

from app.email_delivery import EmailDelivery


class FakeEmailConfig:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.smtp_host = "smtp.example.com"
        self.smtp_port = 587
        self.smtp_user = "atlas@example.com"
        self.smtp_password = "password"
        self.sender = "atlas@example.com"
        self.recipients = ["owner@example.com"]
        self.use_ssl = False
        self.use_starttls = True

    def validate(self):
        return None


class CapturingEmailDelivery(EmailDelivery):
    def __init__(self, config):
        super().__init__(config=config)
        self.sent_message = None

    def _send(self, message):
        self.sent_message = message


class EmailDeliveryTests(unittest.TestCase):
    def test_send_report_uses_custom_subject_and_body(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            markdown_path = Path(temp_dir) / "weekly_summary.md"
            markdown_path.write_text("# Weekly Summary", encoding="utf-8")

            delivery = CapturingEmailDelivery(FakeEmailConfig(enabled=True))

            sent = delivery.send_report(
                markdown_path,
                subject="Atlas Weekly Research Summary",
                body="Custom weekly body.\n",
            )

        self.assertTrue(sent)
        self.assertEqual(delivery.sent_message["Subject"], "Atlas Weekly Research Summary")
        self.assertIn("Custom weekly body.", delivery.sent_message.get_body().get_content())

    def test_send_report_returns_false_when_disabled(self):
        delivery = CapturingEmailDelivery(FakeEmailConfig(enabled=False))

        sent = delivery.send_report("unused.md")

        self.assertFalse(sent)
        self.assertIsNone(delivery.sent_message)


if __name__ == "__main__":
    unittest.main()
