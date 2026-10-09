import logging
import time
import uuid


request_logger = logging.getLogger("blog.request")


class ObservabilityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.perf_counter()
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        try:
            response = self.get_response(request)
        except Exception:
            request_logger.exception(
                "Unhandled request exception",
                extra={
                    "event": "request_error",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.path,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                    "status_code": 500,
                },
            )
            raise

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        if not request.path.startswith(("/static/", "/media/", "/health/")):
            status = response.status_code
            log = request_logger.error if status >= 500 else request_logger.warning if status >= 400 else request_logger.info
            log(
                "%s %s completed with %s",
                request.method,
                request.path,
                status,
                extra={
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.path,
                    "status_code": status,
                    "duration_ms": duration_ms,
                },
            )
        return response


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
