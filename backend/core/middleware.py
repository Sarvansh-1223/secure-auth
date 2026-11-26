class ApiSecurityHeadersMiddleware:
    """Auth responses must never be cached; add a few defensive headers."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["Cache-Control"] = "no-store"
        response["Pragma"] = "no-cache"
        response.setdefault("X-Content-Type-Options", "nosniff")
        response.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        return response
