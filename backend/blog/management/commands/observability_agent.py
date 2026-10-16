"""서비스 상태 점검과 WAF 로그 전달을 하나의 관측성 에이전트로 실행합니다."""

import queue
import threading

from django.core.management.base import BaseCommand, CommandError

from .export_waf_audit import export_waf_events
from .observability_heartbeat import monitor_services


class Command(BaseCommand):
    help = "서비스 상태 점검과 WAF 감사 로그 전달을 함께 실행합니다."

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=int, default=30)
        parser.add_argument("--waf-log-path", default="/var/log/waf/audit/audit.json")

    def handle(self, *args, **options):
        stop_event = threading.Event()
        failures = queue.Queue()

        def run_worker(name, target, *worker_args):
            """작업 하나가 끝나면 정상 반환도 장애로 간주해 컨테이너를 재시작시킵니다."""

            try:
                target(*worker_args, stop_event=stop_event)
            except Exception as error:  # 관리 명령 최상단에서 장애를 한곳으로 전달합니다.
                failures.put((name, error))
            else:
                failures.put((name, RuntimeError("작업이 예기치 않게 종료됐습니다.")))

        workers = [
            threading.Thread(
                name="서비스-상태-점검",
                target=run_worker,
                args=("서비스 상태 점검", monitor_services, options["interval"]),
                daemon=True,
            ),
            threading.Thread(
                name="WAF-로그-전달",
                target=run_worker,
                args=("WAF 로그 전달", export_waf_events, options["waf_log_path"]),
                daemon=True,
            ),
        ]

        self.stdout.write("통합 관측성 에이전트를 시작합니다.")
        for worker in workers:
            worker.start()

        try:
            failed_name, error = failures.get()
        except KeyboardInterrupt:
            stop_event.set()
            for worker in workers:
                worker.join(timeout=5)
            self.stdout.write("통합 관측성 에이전트를 종료합니다.")
            return

        stop_event.set()
        raise CommandError(f"{failed_name} 작업이 중단됐습니다: {error}")
