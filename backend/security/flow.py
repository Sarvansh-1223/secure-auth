"""Shared "verify a code" flow used by login and registration verification."""
from accounts.identifiers import find_user, parse_identifier
from core.utils import get_client_ip, get_user_agent
from otp import services as otp_services
from security import lockout


def verify_code_flow(request, raw_identifier: str, code: str, purpose: str):
    """
    Returns (user, identifier) on success, raises ApiError otherwise.

    Order matters: lockout guard FIRST (nothing is evaluated while locked), then verification, then
    success/failure bookkeeping. Unknown identifiers and wrong codes take the same path and yield the
    same response. The lockout subject is the user row whenever an active account exists (so email and
    phone logins share ONE counter), otherwise a keyed hash of the identifier.
    """
    ident = parse_identifier(raw_identifier)
    user = find_user(ident)
    if user is not None and not user.is_active:
        user = None

    ip, ua = get_client_ip(request), get_user_agent(request)
    lockout.guard(user, ident.digest, ip)

    may_verify = user is not None and (purpose == "REGISTER" or user.is_identifier_verified(ident.kind))
    if may_verify:
        ok = otp_services.verify(user, purpose, code)
    else:
        otp_services.verify_dummy(code)
        ok = False

    if not ok:
        raise lockout.record_failure(user, ident.digest, "OTP", ip, ua, "bad_code")

    lockout.record_success(user, ident.digest, "OTP", ip, ua)
    return user, ident
