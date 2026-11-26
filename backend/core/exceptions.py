"""
Uniform API error envelope:

    {"error": {"code": "SOME_CODE", "message": "Human readable", "details": {...}}}

Authentication failures deliberately use generic messages so responses never reveal
whether an account exists.
"""
from django.http import Http404
from rest_framework import exceptions as drf
from rest_framework.response import Response


class ApiError(drf.APIException):
    status_code = 400
    code = "BAD_REQUEST"
    default_detail = "Request could not be processed."

    def __init__(self, message=None, *, code=None, details=None, headers=None):
        super().__init__(message or self.default_detail)
        if code:
            self.code = code
        self.details = details or {}
        self.headers = headers or {}


class InvalidCredentials(ApiError):
    """Wrong / expired / reused code, or unknown account: always the same generic message."""

    status_code = 400
    code = "INVALID_CREDENTIALS"
    default_detail = "That didn't work. Check your details and try again."


class AccountLocked(ApiError):
    status_code = 423
    code = "ACCOUNT_LOCKED"
    default_detail = "Too many unsuccessful attempts. Try again later."

    def __init__(self, retry_after_seconds, locked_until):
        retry_after_seconds = max(int(retry_after_seconds), 1)
        super().__init__(
            details={"retry_after_seconds": retry_after_seconds, "locked_until": locked_until.isoformat()},
            headers={"Retry-After": str(retry_after_seconds)},
        )


class ResendThrottled(ApiError):
    status_code = 429
    code = "RESEND_THROTTLED"
    default_detail = "Please wait before requesting another code."

    def __init__(self, retry_after_seconds):
        retry_after_seconds = max(int(retry_after_seconds), 1)
        super().__init__(
            details={"retry_after_seconds": retry_after_seconds},
            headers={"Retry-After": str(retry_after_seconds)},
        )


class SessionError(ApiError):
    status_code = 401


class SessionReplaced(SessionError):
    code = "SESSION_REPLACED"
    default_detail = "You were signed out because your account was signed in on another device."


class SessionEnded(SessionError):
    code = "SESSION_ENDED"
    default_detail = "This session has ended. Please sign in again."


class SessionExpired(SessionError):
    code = "SESSION_EXPIRED"
    default_detail = "Your session expired. Please sign in again."


class SessionInvalid(SessionError):
    code = "SESSION_INVALID"
    default_detail = "Please sign in to continue."


def _envelope(code, message, details=None):
    return {"error": {"code": code, "message": message, "details": details or {}}}


def api_exception_handler(exc, context):
    # Imported lazily: rest_framework.views imports settings that import this module (cycle).
    from rest_framework.views import exception_handler as drf_handler

    if isinstance(exc, ApiError):
        resp = Response(_envelope(exc.code, str(exc.detail), exc.details), status=exc.status_code)
        for k, v in exc.headers.items():
            resp[k] = v
        return resp

    if isinstance(exc, Http404):
        exc = drf.NotFound()

    response = drf_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, drf.ValidationError):
        data = _envelope("VALIDATION_ERROR", "Please correct the highlighted fields.", _flatten(exc.detail))
    elif isinstance(exc, drf.Throttled):
        wait = int(exc.wait or 1)
        data = _envelope("RATE_LIMITED", "Too many requests. Please slow down.", {"retry_after_seconds": wait})
    elif isinstance(exc, drf.NotAuthenticated):
        data = _envelope("NOT_AUTHENTICATED", "Please sign in to continue.")
        response.status_code = 401
    elif isinstance(exc, drf.AuthenticationFailed):
        data = _envelope("NOT_AUTHENTICATED", "Please sign in to continue.")
        response.status_code = 401
    elif isinstance(exc, drf.PermissionDenied):
        text = str(exc.detail)
        code = "CSRF_FAILED" if text.startswith("CSRF") else "FORBIDDEN"
        data = _envelope(code, "Request was rejected." if code == "CSRF_FAILED" else "Not allowed.")
    elif isinstance(exc, drf.NotFound):
        data = _envelope("NOT_FOUND", "Not found.")
    elif isinstance(exc, drf.MethodNotAllowed):
        data = _envelope("METHOD_NOT_ALLOWED", "Method not allowed.")
    elif isinstance(exc, (drf.ParseError, drf.UnsupportedMediaType)):
        data = _envelope("BAD_REQUEST", "Malformed request body.")
    else:
        data = _envelope("ERROR", "Request failed.")
    response.data = data
    return response


def _flatten(detail):
    """Turn DRF ErrorDetail structures into {field: [messages]} plain JSON."""
    if isinstance(detail, dict):
        return {k: _flatten(v) for k, v in detail.items()}
    if isinstance(detail, (list, tuple)):
        return [_flatten(v) if isinstance(v, (dict, list)) else str(v) for v in detail]
    return [str(detail)]
