class SameOriginFrameProtectionMiddleware:
    """Allow SimpleUI's same-origin frames while blocking external embedding."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault(
            "Content-Security-Policy",
            "frame-ancestors 'self'",
        )
        return response
