from unittest.mock import MagicMock, patch

from cqc_lem.utilities.email import generate_pin, hash_pin, send_pin_email


class TestGeneratePin:
    def test_is_six_digits(self):
        pin = generate_pin()
        assert len(pin) == 6
        assert pin.isdigit()

    def test_zero_padded(self):
        pin = generate_pin()
        assert len(pin) == 6

    def test_returns_string(self):
        assert isinstance(generate_pin(), str)


class TestHashPin:
    def test_deterministic(self):
        h1 = hash_pin("123456", "test@example.com")
        h2 = hash_pin("123456", "test@example.com")
        assert h1 == h2

    def test_different_pins_produce_different_hashes(self):
        h1 = hash_pin("000000", "test@example.com")
        h2 = hash_pin("999999", "test@example.com")
        assert h1 != h2

    def test_different_emails_produce_different_hashes(self):
        h1 = hash_pin("123456", "a@example.com")
        h2 = hash_pin("123456", "b@example.com")
        assert h1 != h2

    def test_returns_64_char_hex(self):
        h = hash_pin("123456", "test@example.com")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


class TestSendPinEmailSendGrid:
    @patch("cqc_lem.utilities.email.SENDGRID_API_KEY", "sg_test_key")
    @patch("cqc_lem.utilities.email.SMTP_USER", None)
    @patch("cqc_lem.utilities.email.SMTP_PASSWORD", None)
    @patch("sendgrid.SendGridAPIClient")
    def test_sendgrid_success_returns_true_not_bypassed(self, mock_sg_class):
        mock_sg = MagicMock()
        mock_sg.send.return_value = MagicMock(status_code=202)
        mock_sg_class.return_value = mock_sg

        success, bypassed = send_pin_email("test@example.com", "123456")

        assert success is True
        assert bypassed is False
        mock_sg.send.assert_called_once()

    @patch("cqc_lem.utilities.email.SENDGRID_API_KEY", "sg_test_key")
    @patch("cqc_lem.utilities.email.SMTP_USER", None)
    @patch("cqc_lem.utilities.email.SMTP_PASSWORD", None)
    @patch("sendgrid.SendGridAPIClient")
    def test_sendgrid_failure_returns_false_not_bypassed(self, mock_sg_class):
        mock_sg = MagicMock()
        mock_sg.send.side_effect = Exception("Network error")
        mock_sg_class.return_value = mock_sg

        success, bypassed = send_pin_email("test@example.com", "123456")

        assert success is False
        assert bypassed is False

    @patch("cqc_lem.utilities.email.SENDGRID_API_KEY", "sg_test_key")
    @patch("cqc_lem.utilities.email.SMTP_USER", None)
    @patch("cqc_lem.utilities.email.SMTP_PASSWORD", None)
    @patch("sendgrid.SendGridAPIClient")
    def test_new_user_flag_does_not_crash(self, mock_sg_class):
        mock_sg = MagicMock()
        mock_sg_class.return_value = mock_sg

        send_pin_email("new@example.com", "000001", is_new_user=True)

        mock_sg.send.assert_called_once()


class TestSendPinEmailSmtpFallback:
    @patch("cqc_lem.utilities.email.SENDGRID_API_KEY", None)
    @patch("cqc_lem.utilities.email.SMTP_USER", "user@gmail.com")
    @patch("cqc_lem.utilities.email.SMTP_PASSWORD", "app_password")
    @patch("cqc_lem.utilities.email.smtplib.SMTP")
    def test_smtp_success_when_sendgrid_missing(self, mock_smtp_class):
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        success, bypassed = send_pin_email("test@example.com", "654321")

        assert success is True
        assert bypassed is False

    @patch("cqc_lem.utilities.email.SENDGRID_API_KEY", "sg_key")
    @patch("cqc_lem.utilities.email.SMTP_USER", "user@gmail.com")
    @patch("cqc_lem.utilities.email.SMTP_PASSWORD", "app_password")
    @patch("cqc_lem.utilities.email.smtplib.SMTP")
    @patch("sendgrid.SendGridAPIClient")
    def test_smtp_fallback_used_when_sendgrid_fails(self, mock_sg_class, mock_smtp_class):
        mock_sg = MagicMock()
        mock_sg.send.side_effect = Exception("SendGrid down")
        mock_sg_class.return_value = mock_sg

        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        success, bypassed = send_pin_email("test@example.com", "654321")

        assert success is True
        assert bypassed is False

    @patch("cqc_lem.utilities.email.SENDGRID_API_KEY", None)
    @patch("cqc_lem.utilities.email.SMTP_USER", "user@gmail.com")
    @patch("cqc_lem.utilities.email.SMTP_PASSWORD", "app_password")
    @patch("cqc_lem.utilities.email.smtplib.SMTP")
    def test_smtp_failure_returns_false(self, mock_smtp_class):
        mock_smtp_class.side_effect = Exception("SMTP connection refused")

        success, bypassed = send_pin_email("test@example.com", "654321")

        assert success is False
        assert bypassed is False


class TestSendPinEmailBypass:
    @patch("cqc_lem.utilities.email.SENDGRID_API_KEY", None)
    @patch("cqc_lem.utilities.email.SMTP_USER", None)
    @patch("cqc_lem.utilities.email.SMTP_PASSWORD", None)
    def test_bypass_when_no_provider_configured(self):
        success, bypassed = send_pin_email("test@example.com", "123456")

        assert success is True
        assert bypassed is True

    @patch("cqc_lem.utilities.email.SENDGRID_API_KEY", None)
    @patch("cqc_lem.utilities.email.SMTP_USER", "user@gmail.com")
    @patch("cqc_lem.utilities.email.SMTP_PASSWORD", None)
    @patch("cqc_lem.utilities.email.smtplib.SMTP")
    def test_no_bypass_when_smtp_user_set_but_password_missing(self, mock_smtp_class):
        # SMTP_USER without SMTP_PASSWORD → treated as no SMTP provider → bypass
        mock_smtp_class.side_effect = Exception("Should not be called")

        success, bypassed = send_pin_email("test@example.com", "123456")

        # No provider configured (password missing), so bypass
        assert success is True
        assert bypassed is True
        mock_smtp_class.assert_not_called()
