import hashlib
import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Tuple

from cqc_lem.utilities.env_constants import (
    SENDGRID_API_KEY,
    SENDGRID_FROM_EMAIL,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
)
from cqc_lem.utilities.logger import myprint


def generate_pin() -> str:
    return str(random.randint(0, 999999)).zfill(6)


def hash_pin(pin: str, email: str) -> str:
    return hashlib.sha256(f"{pin}{email}".encode()).hexdigest()


def _build_html(pin: str, action: str) -> str:
    return f"""
    <html><body>
    <h2>Your LinkedIn Engagement Manager Verification Code</h2>
    <p>Enter the following code to {action}:</p>
    <h1 style="letter-spacing:0.3em;font-family:monospace;">{pin}</h1>
    <p>This code expires in <strong>10 minutes</strong>.</p>
    <p style="color:#888;font-size:12px;">If you did not request this, you can safely ignore this email.</p>
    </body></html>
    """


def _send_via_sendgrid(to_email: str, html_content: str) -> bool:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    message = Mail(
        from_email=SENDGRID_FROM_EMAIL,
        to_emails=to_email,
        subject="Your LEM Verification Code",
        html_content=html_content,
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        myprint(f"PIN email sent via SendGrid to {to_email}")
        return True
    except Exception as e:
        myprint(f"SendGrid send failed for {to_email}: {e}")
        return False


def _send_via_smtp(to_email: str, html_content: str) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your LEM Verification Code"
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg.attach(MIMEText(html_content, "html"))
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        myprint(f"PIN email sent via SMTP to {to_email}")
        return True
    except Exception as e:
        myprint(f"SMTP send failed for {to_email}: {e}")
        return False


def send_pin_email(to_email: str, pin: str, is_new_user: bool = False) -> Tuple[bool, bool]:
    """Send a PIN email using the best available provider.

    Returns (success, bypassed):
      - (True, False)  — email was sent successfully
      - (False, False) — a provider is configured but the send failed
      - (True, True)   — no provider is configured; PIN step should be skipped
    """
    action = "create your account" if is_new_user else "sign in"
    html = _build_html(pin, action)

    has_sendgrid = bool(SENDGRID_API_KEY)
    has_smtp = bool(SMTP_USER) and bool(SMTP_PASSWORD)

    if not has_sendgrid and not has_smtp:
        myprint("No email provider configured — bypassing PIN verification")
        return True, True

    if has_sendgrid:
        sent = _send_via_sendgrid(to_email, html)
        if sent:
            return True, False
        myprint("SendGrid failed — trying SMTP fallback")

    if has_smtp:
        sent = _send_via_smtp(to_email, html)
        return sent, False

    # SendGrid was configured but failed; no SMTP fallback available
    return False, False
