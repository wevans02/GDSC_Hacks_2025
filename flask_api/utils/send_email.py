# utils/emailer.py
import smtplib
from email.mime.text import MIMEText
from . import config

def send_email(subject: str, body: str) -> bool:
    """
    Try to send an email via SMTP creds in env. Return True/False.
    """
    if not (config.SMTP_USER and config.SMTP_PASS and config.FEEDBACK_EMAIL):
        # Not configured
        return False

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = config.SMTP_USER
    msg["To"] = config.FEEDBACK_EMAIL

    try:
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASS)
            server.sendmail(config.SMTP_USER, [config.FEEDBACK_EMAIL], msg.as_string())
        return True
    except Exception:
        return False
