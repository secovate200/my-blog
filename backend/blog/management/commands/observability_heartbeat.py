import logging
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand


logger = logging.getLogger("blog.heartbeat")

SERVICE_ENDPOINTS = {
    # 감시 에이전트는 별도 컨테이너에서 실행되므로 Compose 서비스 이름으로 접근합니다.
    "backend": "http://backend:8000/health/",
    "waf": "http://waf:8080/health/",
    "blog-front": "http://blog-front/",
    "dashboard-front": "http://dashboard-front/",
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


def monitor_services(interval=30, stop_event=None):
    """모든 서비스 상태를 주기적으로 확인하고 종료 신호에 즉시 반응합니다."""

    interval = max(10, interval)
    failures = {service: 0 for service in SERVICE_ENDPOINTS}
    logger.info("관측성 서비스 감시를 시작합니다. 점검 주기=%s초", interval)
    while stop_event is None or not stop_event.is_set():
        logger.info(
            "백엔드가 정상적으로 동작 중입니다.",
            extra={"event": "heartbeat", "status": "up"},
        )
        for service, url in SERVICE_ENDPOINTS.items():
            is_up, status_code = service_is_up(url)
            failures[service] = 0 if is_up else failures[service] + 1
            if not is_up and failures[service] < 2:
                logger.warning("서비스 %s의 상태 점검이 한 차례 실패했습니다.", service)
                continue
            level = logging.INFO if is_up else logging.ERROR
            logger.log(
                level,
                "서비스 %s의 상태는 %s입니다.",
                service,
                "정상" if is_up else "장애",
                extra={
                    "event": "service_health",
                    "target_service": service,
                    "status": "up" if is_up else "down",
                    "status_code": status_code,
                },
            )

        # Event.wait를 사용하면 컨테이너 종료 시 긴 점검 주기를 기다리지 않습니다.
        if stop_event is not None:
            stop_event.wait(interval)
        else:
            time.sleep(interval)


class Command(BaseCommand):
    help = "OpenObserve에 서비스 heartbeat 로그를 주기적으로 전송합니다."

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=int, default=30)

    def handle(self, *args, **options):
        monitor_services(options["interval"])
