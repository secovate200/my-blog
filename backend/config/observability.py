import base64
import json
import logging
import queue
import threading
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


SAFE_EXTRA_FIELDS = {
    "event", "request_id", "method", "path", "status_code", "duration_ms",
    "status", "service", "error_count", "request_count", "max_duration_ms",
    "target_service",
    "schema_version", "provider", "engine", "rule_id", "severity",
    "attack_type", "action", "matched_field", "matched_data", "client_ip",
    "client_fingerprint",
}


def record_to_event(record):
    event = {
        "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
        "service": getattr(record, "service", "backend"),
        "environment": getattr(settings, "OBSERVABILITY_ENVIRONMENT", "development"),
        "level": record.levelname.lower(),
        "logger": record.name,
        "message": record.getMessage(),
    }
    for key, value in record.__dict__.items():
        if key in SAFE_EXTRA_FIELDS and key not in event:
            event[key] = value if isinstance(value, (str, int, float, bool, type(None))) else str(value)
    if record.exc_info:
        event["exception"] = logging.Formatter().formatException(record.exc_info)
    return event


class StructuredJsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps(record_to_event(record), ensure_ascii=False, separators=(",", ":"))


class OpenObserveHandler(logging.Handler):
    """Send logs out of band. Queue saturation or collector failure never blocks requests."""

    _queue = queue.Queue(maxsize=1000)
    _worker = None
    _lock = threading.Lock()

    def emit(self, record):
        if not getattr(settings, "OPENOBSERVE_URL", ""):
            return
        self._ensure_worker()
        try:
            self._queue.put_nowait(record_to_event(record))
        except queue.Full:
            pass

    @classmethod
    def _ensure_worker(cls):
        if cls._worker and cls._worker.is_alive():
            return
        with cls._lock:
            if cls._worker and cls._worker.is_alive():
                return
            cls._worker = threading.Thread(
                target=cls._run,
                name="openobserve-log-exporter",
                daemon=True,
            )
            cls._worker.start()

    @classmethod
    def _run(cls):
        while True:
            first = cls._queue.get()
            batch = [first]
            while len(batch) < 100:
                try:
                    batch.append(cls._queue.get_nowait())
                except queue.Empty:
                    break
            cls._send(batch)

    @staticmethod
    def _send(events):
        base_url = settings.OPENOBSERVE_URL.rstrip("/")
        endpoint = f"{base_url}/api/{settings.OPENOBSERVE_ORG}/{settings.OPENOBSERVE_STREAM}/_json"
        credentials = f"{settings.OPENOBSERVE_USER}:{settings.OPENOBSERVE_PASSWORD}"
        authorization = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
        request = Request(
            endpoint,
            data=json.dumps(events, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Basic {authorization}",
                "Content-Type": "application/json",
                "User-Agent": "my-blog-observability/1.0",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=2):
                pass
        except (HTTPError, URLError, TimeoutError, OSError):
            # Never log here: doing so would recursively enqueue the same failure.
            pass
