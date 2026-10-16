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
                "요청 처리 중 예기치 않은 오류가 발생했습니다.",
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
            log = (
                request_logger.error
                if status >= 500
                else request_logger.warning
                if status >= 400
                else request_logger.info
            )
            log(
                "%s %s 요청이 HTTP %s 상태로 완료되었습니다.",
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
    """동일 출처 프레임은 허용하고 외부 사이트의 화면 삽입은 차단합니다."""

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
