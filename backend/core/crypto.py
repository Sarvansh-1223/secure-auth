"""Small, audited-in-one-place cryptographic helpers."""
import hashlib
import hmac
import secrets

from django.conf import settings


def _b(value) -> bytes:
    return value if isinstance(value, bytes) else str(value).encode("utf-8")


def hmac_hex(*parts) -> str:
    """HMAC-SHA256 keyed with the server pepper. Parts are length-unambiguous (0x1f separated)."""
    msg = b"\x1f".join(_b(p) for p in parts)
    return hmac.new(_b(settings.AUTH_PEPPER), msg, hashlib.sha256).hexdigest()


def sha256_hex(value) -> str:
    """Plain SHA-256: fine for high-entropy random tokens (not for low-entropy secrets like OTPs)."""
    return hashlib.sha256(_b(value)).hexdigest()


def constant_time_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(_b(a), _b(b))


def random_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def random_digits(length: int) -> str:
    """Uniform, cryptographically secure zero-padded numeric code."""
    return str(secrets.randbelow(10**length)).zfill(length)
