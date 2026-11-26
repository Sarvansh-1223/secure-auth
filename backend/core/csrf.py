from django.middleware.csrf import CsrfViewMiddleware
from rest_framework.exceptions import PermissionDenied


class _CSRFCheck(CsrfViewMiddleware):
    def _reject(self, request, reason):
        return reason  # return the reason instead of an HttpResponse


def enforce_csrf(request):
    """Same approach as DRF's SessionAuthentication: run Django's CSRF check by hand."""
    check = _CSRFCheck(lambda r: None)
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    if reason:
        raise PermissionDenied(f"CSRF Failed: {reason}")
