"""
WebAuthn (py_webauthn) registration + authentication.

* Challenges are random, stored server-side, single-use and expire after WEBAUTHN_CHALLENGE_TTL_SECONDS.
* The server verifies challenge, origin, RP ID, user-verification flag and the assertion signature.
* Sign counters are tracked to help detect cloned authenticators.
* For unknown identifiers (or users with no credentials) a deterministic decoy credential id is returned so the
  options response doesn't reveal whether an account / biometric exists.
"""
import json
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorAttachment,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from core.crypto import hmac_hex, sha256_hex
from core.exceptions import ApiError, InvalidCredentials
from security import lockout
from security.models import LoginAttempt

from .models import BiometricCredential, WebAuthnChallenge


class WebAuthnFailed(ApiError):
    status_code = 400
    code = "WEBAUTHN_FAILED"
    default_detail = "Biometric verification failed. Try again or use a verification code."


def _store_challenge(challenge: bytes, purpose: str, user=None, digest: str = "") -> None:
    now = timezone.now()
    WebAuthnChallenge.objects.filter(expires_at__lt=now).delete()  # opportunistic cleanup
    WebAuthnChallenge.objects.create(
        user=user,
        identifier_hash=digest,
        challenge_hash=sha256_hex(bytes_to_base64url(challenge)),
        challenge=challenge,
        purpose=purpose,
        expires_at=now + timedelta(seconds=settings.WEBAUTHN_CHALLENGE_TTL_SECONDS),
    )


def _challenge_from_client_data(credential: dict) -> str:
    try:
        client_data = json.loads(base64url_to_bytes(credential["response"]["clientDataJSON"]))
        value = client_data["challenge"]
        if not isinstance(value, str):
            raise ValueError
        return value
    except Exception:
        raise WebAuthnFailed()


def _pop_challenge(challenge_b64: str, purpose: str, user=None) -> WebAuthnChallenge:
    """Fetch AND delete the challenge atomically (one use only)."""
    with transaction.atomic():
        qs = WebAuthnChallenge.objects.select_for_update().filter(
            challenge_hash=sha256_hex(challenge_b64), purpose=purpose, expires_at__gt=timezone.now()
        )
        if user is not None:
            qs = qs.filter(user=user)
        row = qs.first()
        if row is None:
            raise WebAuthnFailed()
        WebAuthnChallenge.objects.filter(pk=row.pk).delete()
        return row


def _json(options) -> dict:
    return json.loads(options_to_json(options))


# ------------------------------------------------------------------ registration
def begin_registration(user, attachment: str) -> dict:
    existing = BiometricCredential.objects.filter(user=user, revoked_at__isnull=True)
    selection = AuthenticatorSelectionCriteria(
        authenticator_attachment=(
            AuthenticatorAttachment.PLATFORM if attachment == "platform" else AuthenticatorAttachment.CROSS_PLATFORM
        ),
        resident_key=ResidentKeyRequirement.PREFERRED,
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    name = user.email or user.phone_e164
    options = generate_registration_options(
        rp_id=settings.WEBAUTHN_RP_ID,
        rp_name=settings.WEBAUTHN_RP_NAME,
        user_id=user.public_id.bytes,
        user_name=name,
        user_display_name=name,
        authenticator_selection=selection,
        exclude_credentials=[
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id)) for c in existing
        ],
        timeout=60000,
    )
    _store_challenge(options.challenge, WebAuthnChallenge.Purpose.REGISTER, user=user)
    return _json(options)


def finish_registration(user, credential: dict, nickname: str, attachment: str, device) -> BiometricCredential:
    challenge_b64 = _challenge_from_client_data(credential)
    row = _pop_challenge(challenge_b64, WebAuthnChallenge.Purpose.REGISTER, user=user)
    try:
        verified = verify_registration_response(
            credential=credential,
            expected_challenge=bytes(row.challenge),
            expected_rp_id=settings.WEBAUTHN_RP_ID,
            expected_origin=settings.WEBAUTHN_ORIGINS,
            require_user_verification=True,
        )
    except Exception:
        raise WebAuthnFailed("Could not verify the new credential.")

    transports = (credential.get("response") or {}).get("transports") or []
    try:
        with transaction.atomic():
            return BiometricCredential.objects.create(
                user=user,
                device=device,
                credential_id=bytes_to_base64url(verified.credential_id),
                public_key=verified.credential_public_key,
                sign_count=verified.sign_count,
                attachment=attachment,
                transports=[t for t in transports if isinstance(t, str)][:6],
                nickname=(nickname or "").strip()[:100] or "Biometric credential",
                backed_up=bool(getattr(verified, "credential_backed_up", False)),
            )
    except IntegrityError:
        raise WebAuthnFailed("This credential is already registered.")


# ------------------------------------------------------------------ authentication
def begin_authentication(identifier, user, ip) -> dict:
    digest = identifier.digest
    lockout.guard(user, digest, ip)  # locked accounts get no challenge

    creds = []
    if user is not None and user.is_active:
        creds = list(BiometricCredential.objects.filter(user=user, revoked_at__isnull=True))

    if creds:
        allow = [PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id)) for c in creds]
    else:  # decoy: stable per identifier so repeated calls look identical
        allow = [PublicKeyCredentialDescriptor(id=bytes.fromhex(hmac_hex("decoy", digest))[:32])]

    options = generate_authentication_options(
        rp_id=settings.WEBAUTHN_RP_ID,
        allow_credentials=allow,
        user_verification=UserVerificationRequirement.REQUIRED,
        timeout=60000,
    )
    _store_challenge(
        options.challenge,
        WebAuthnChallenge.Purpose.AUTHENTICATE,
        user=user if creds else None,
        digest=digest,
    )
    return _json(options)


def finish_authentication(credential: dict, ip, user_agent):
    """Returns the authenticated user; raises ApiError otherwise. Feeds the lockout counter."""
    challenge_b64 = _challenge_from_client_data(credential)
    try:
        row = _pop_challenge(challenge_b64, WebAuthnChallenge.Purpose.AUTHENTICATE)
    except WebAuthnFailed:
        # Unattributable failure: still visible to the per-IP limiter.
        LoginAttempt.objects.create(
            identifier_hash="", method="WEBAUTHN", success=False, ip_address=ip,
            user_agent=user_agent, failure_reason="bad_challenge",
        )
        raise

    user, digest = row.user, row.identifier_hash
    lockout.guard(user, digest, ip)

    def fail(reason):
        return lockout.record_failure(user, digest, "WEBAUTHN", ip, user_agent, reason)

    if user is None or not user.is_active:
        raise fail("no_credential")

    cred_id = credential.get("rawId") or credential.get("id")
    cred = BiometricCredential.objects.filter(
        user=user, credential_id=cred_id if isinstance(cred_id, str) else "", revoked_at__isnull=True
    ).first()
    if cred is None:
        raise fail("unknown_credential")

    try:
        verified = verify_authentication_response(
            credential=credential,
            expected_challenge=bytes(row.challenge),
            expected_rp_id=settings.WEBAUTHN_RP_ID,
            expected_origin=settings.WEBAUTHN_ORIGINS,
            credential_public_key=bytes(cred.public_key),
            credential_current_sign_count=cred.sign_count,
            require_user_verification=True,
        )
    except Exception:
        raise fail("bad_assertion")

    BiometricCredential.objects.filter(pk=cred.pk).update(
        sign_count=verified.new_sign_count, last_used_at=timezone.now()
    )
    lockout.record_success(user, digest, "WEBAUTHN", ip, user_agent)
    return user
