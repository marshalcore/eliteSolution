import smtplib
from email.mime.text import MIMEText
from app.core.config import settings


# Ports we want to try in order of preference
SMTP_PORTS = [
    (587, "TLS"),   # modern STARTTLS
    (465, "SSL"),   # legacy SSL
    (2525, "TLS"),  # backup port
    (25, "TLS"),    # traditional SMTP (often blocked)
]


def send_email(to_email: str, subject: str, body: str):
    """
    Send email via SMTP (Brevo relay).
    Tries multiple ports dynamically until one works.
    """
    msg = MIMEText(body, "html")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to_email

    last_error = None

    for port, mode in SMTP_PORTS:
        try:
            if mode == "TLS":
                with smtplib.SMTP(settings.EMAIL_HOST, port, timeout=30) as server:
                    server.starttls()
                    server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                    server.sendmail(settings.EMAIL_FROM, [to_email], msg.as_string())
            elif mode == "SSL":
                with smtplib.SMTP_SSL(settings.EMAIL_HOST, port, timeout=30) as server:
                    server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                    server.sendmail(settings.EMAIL_FROM, [to_email], msg.as_string())

            # ✅ Success → return immediately
            return

        except Exception as e:
            last_error = e
            continue  # try the next port

    # ❌ If all ports fail
    raise RuntimeError(f"Failed to send email via SMTP after trying all ports. Last error: {last_error}")
