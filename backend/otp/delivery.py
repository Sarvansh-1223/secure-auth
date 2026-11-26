"""
OTP delivery adapters.

* Email: Django's email backend (console in dev, SMTP in production).
* SMS: pluggable provider. ``console`` logs the message server-side and is only permitted
  when DEBUG=True; ``twilio`` talks to Twilio's REST API using only the standard library.

The code is NEVER returned from an API response.
"""
import base64
import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail

logger = logging.getLogger("otp.delivery")


def _message(code: str, purpose: str) -> str:
    minutes = max(settings.OTP_TTL_SECONDS // 60, 1)
    action = "verify your account" if purpose == "REGISTER" else "sign in"
    return (
        f"Your verification code to {action} is {code}. It expires in {minutes} minute(s). "
        "If you didn't request it, you can ignore this message."
    )


def send_email(to: str, code: str, purpose: str) -> None:
    send_mail(
        subject="Your verification code",
        message=_message(code, purpose),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to],
        fail_silently=False,
    )


def send_sms(to: str, body: str) -> None:
    provider = settings.SMS_PROVIDER
    if provider == "console":
        if not settings.DEBUG:
            raise ImproperlyConfigured("SMS_PROVIDER=console is only allowed when DEBUG=True.")
        logger.warning("[DEV SMS to %s] %s", to, body)
    elif provider == "twilio":
        _send_twilio(to, body)
    else:
        raise ImproperlyConfigured(f"Unknown SMS_PROVIDER: {provider}")


def _send_twilio(to: str, body: str) -> None:
    sid, token, sender = settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_FROM_NUMBER
    if not (sid and token and sender):
        raise ImproperlyConfigured("Twilio credentials are not configured.")
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    data = urllib.parse.urlencode({"To": to, "From": sender, "Body": body}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{sid}:{token}".encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 (fixed https URL)
            json.load(resp)
    except urllib.error.URLError:
        logger.exception("Twilio delivery failed")
        raise


def deliver_code(*, channel: str, email: str | None, phone: str | None, code: str, purpose: str) -> None:
    if channel == "EMAIL" and email:
        send_email(email, code, purpose)
    elif channel == "SMS" and phone:
        send_sms(phone, _message(code, purpose))


def send_notice(*, email: str | None, phone: str | None, text: str) -> None:
    """Non-secret notifications (e.g. 'you already have an account')."""
    if email:
        send_mail("Account notice", text, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=True)
    elif phone:
        try:
            send_sms(phone, text)
        except Exception:  # notices are best-effort
            logger.exception("notice delivery failed")
