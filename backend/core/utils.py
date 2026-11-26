from django.conf import settings


def get_client_ip(request) -> str | None:
    """REMOTE_ADDR, or the right-most X-Forwarded-For entry only when behind a trusted proxy."""
    if settings.TRUST_PROXY:
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if xff:
            return xff.split(",")[-1].strip() or None
    return request.META.get("REMOTE_ADDR") or None


def get_user_agent(request) -> str:
    return (request.META.get("HTTP_USER_AGENT") or "")[:255]
