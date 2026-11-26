import re
import unicodedata
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError

# Letters (any script) in groups separated by a single space, hyphen, apostrophe or dot.
_SURNAME_RE = re.compile(r"^[^\W\d_]+(?:[ '’.\-][^\W\d_]+)*\.?$")


def validate_surname(value: str) -> str:
    value = unicodedata.normalize("NFC", (value or "").strip())
    value = re.sub(r"\s+", " ", value)
    if not value:
        raise ValidationError("Surname is required.")
    if len(value) > 100:
        raise ValidationError("Surname must be 100 characters or fewer.")
    if not _SURNAME_RE.match(value):
        raise ValidationError("Surname may only contain letters, spaces, hyphens and apostrophes.")
    return value


def _years_between(born: date, today: date) -> int:
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def validate_date_of_birth(value: date, today: date | None = None) -> date:
    today = today or date.today()
    if value > today:
        raise ValidationError("Date of birth cannot be in the future.")
    age = _years_between(value, today)
    if age > settings.MAX_REGISTRATION_AGE_YEARS:
        raise ValidationError("Enter a valid date of birth.")
    if age < settings.MIN_REGISTRATION_AGE_YEARS:
        raise ValidationError(f"You must be at least {settings.MIN_REGISTRATION_AGE_YEARS} years old.")
    return value
