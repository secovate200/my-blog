import logging
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand


logger = logging.getLogger("blog.heartbeat")

SERVICE_ENDPOINTS = {
    "backend": "http://127.0.0.1:8000/health/",
    "waf": "http://waf:8080/health/",
    "blog-front": "http://blog-front:5173/",
    "dashboard-front": "http://dashboard-front:5174/",
    "openobserve": "http://openobserve:5080/healthz",
}


def service_is_up(url):
    request = Request(url, headers={"User-Agent": "SECOVATE200-Monitor/1.0"})
    try:
        with urlopen(request, timeout=4) as response:
            return 200 <= response.status < 500, response.status
    except HTTPError as error:
        return error.code < 500, error.code
    except (URLError, TimeoutError, OSError):
        return False, 0


class Command(BaseCommand):
    help = "OpenObserve에 서비스 heartbeat 로그를 주기적으로 전송합니다."

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=int, default=30)

    def handle(self, *args, **options):
        interval = max(10, options["interval"])
        failures = {service: 0 for service in SERVICE_ENDPOINTS}
        self.stdout.write(f"Observability service monitor started ({interval}s)")
        while True:
            logger.info("Backend heartbeat", extra={"event": "heartbeat", "status": "up"})
            for service, url in SERVICE_ENDPOINTS.items():
                is_up, status_code = service_is_up(url)
                failures[service] = 0 if is_up else failures[service] + 1
                if not is_up and failures[service] < 2:
                    logger.warning("Service %s health check failed once", service)
                    continue
                level = logging.INFO if is_up else logging.ERROR
                logger.log(
                    level,
                    "Service %s is %s",
                    service,
                    "up" if is_up else "down",
                    extra={
                        "event": "service_health",
                        "target_service": service,
                        "status": "up" if is_up else "down",
                        "status_code": status_code,
                    },
                )
            time.sleep(interval)
