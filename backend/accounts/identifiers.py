"""Normalisation of the login identifier (email or phone number)."""
from dataclasses import dataclass

import phonenumbers
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from core.crypto import hmac_hex


@dataclass(frozen=True)
class Identifier:
    kind: str | None  # "email" | "phone" | None (unparseable)
    value: str

    @property
    def digest(self) -> str:
        """Keyed hash used for lockout / throttling of identifiers without leaking them to the DB."""
        return hmac_hex("identifier", self.kind or "raw", self.value)

    @property
    def valid(self) -> bool:
        return self.kind is not None


def normalize_email(raw: str) -> str:
    value = (raw or "").strip().lower()
    validate_email(value)
    return value


def normalize_phone(raw: str) -> str:
    """Strict international format: must start with '+' and be a valid number. Returns E.164."""
    value = (raw or "").strip()
    if not value.startswith("+"):
        raise ValidationError("Use international format, e.g. +14155552671.")
    try:
        parsed = phonenumbers.parse(value, None)
    except phonenumbers.NumberParseException:
        raise ValidationError("Enter a valid phone number.")
    if not phonenumbers.is_valid_number(parsed):
        raise ValidationError("Enter a valid phone number.")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def parse_identifier(raw: str) -> Identifier:
    """Never raises: unparseable input becomes a 'raw' identifier so callers stay uniform."""
    raw = (raw or "").strip()[:254]
    try:
        if "@" in raw:
            return Identifier("email", normalize_email(raw))
        return Identifier("phone", normalize_phone(raw))
    except ValidationError:
        return Identifier(None, raw.lower())


def find_user(identifier: Identifier):
    from .models import User

    if not identifier.valid:
        return None
    field = "email" if identifier.kind == "email" else "phone_e164"
    return User.objects.filter(**{field: identifier.value}).select_related("profile").first()
