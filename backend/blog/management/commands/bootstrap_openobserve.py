import base64
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "OpenObserve Discord destination과 기본 장애 알림을 멱등적으로 구성합니다."

    def _request(self, method, path, payload=None):
        credentials = f"{settings.OPENOBSERVE_USER}:{settings.OPENOBSERVE_PASSWORD}"
        authorization = base64.b64encode(credentials.encode()).decode()
        request = Request(
            f"{settings.OPENOBSERVE_URL.rstrip('/')}{path}",
            data=None if payload is None else json.dumps(payload).encode(),
            headers={"Authorization": f"Basic {authorization}", "Content-Type": "application/json"},
            method=method,
        )
        try:
            with urlopen(request, timeout=5) as response:
                return json.loads(response.read() or b"{}")
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"OpenObserve API {method} {path} failed ({error.code}): {detail}"
            ) from error

    def _upsert(self, collection_path, item_path, payload):
        try:
            self._request("GET", item_path)
        except RuntimeError as error:
            if "(404)" not in str(error):
                raise
            self._request("POST", collection_path, payload)
        else:
            self._request("PUT", item_path, payload)

    def handle(self, *args, **options):
        if not settings.OPENOBSERVE_URL:
            return
        for attempt in range(30):
            try:
                self._request("GET", "/healthz")
                break
            except (HTTPError, URLError, TimeoutError, OSError):
                if attempt == 29:
                    self.stderr.write("OpenObserve가 준비되지 않아 자동 구성을 건너뜁니다.")
                    return
                time.sleep(2)

        if not settings.DISCORD_ALERT_WEBHOOK_URL:
            self.stdout.write("DISCORD_ALERT_WEBHOOK_URL이 없어 Discord 알림 자동 구성을 건너뜁니다.")
            return

        org = settings.OPENOBSERVE_ORG
        stream = settings.OPENOBSERVE_STREAM
        template = {
            "name": "discord_incident",
            "title": "SECOVATE200 장애 알림",
            "body": json.dumps({
                "username": "SECOVATE200 Monitor",
                "allowed_mentions": {"parse": []},
                "content": "🚨 **{alert_name}**\\n스트림: {stream_name}\\n{rows}",
            }, ensure_ascii=False),
            "type": "http",
            "isDefault": False,
        }
        self._upsert(
            f"/api/{org}/alerts/templates",
            f"/api/{org}/alerts/templates/discord_incident",
            template,
        )
        destination = {
            "name": "discord_alerts",
            "url": settings.DISCORD_ALERT_WEBHOOK_URL,
            "method": "post",
            "type": "http",
            "template": "discord_incident",
            "skip_tls_verify": False,
            "headers": {"Content-Type": "application/json"},
        }
        self._upsert(
            f"/api/{org}/alerts/destinations?module=alert",
            f"/api/{org}/alerts/destinations/discord_alerts?module=alert",
            destination,
        )

        existing = self._request("GET", f"/api/v2/{org}/alerts").get("list", [])
        existing_by_name = {item.get("name"): item for item in existing}
        # WAF notifications are sent directly by export_waf_audit for sub-second delivery.
        # Remove the older OpenObserve WAF rule to prevent delayed duplicate messages.
        legacy_waf_alert = existing_by_name.pop("waf_attack_detected", None)
        if legacy_waf_alert:
            self._request(
                "DELETE",
                f"/api/v2/{org}/alerts/{legacy_waf_alert['alert_id']}",
            )
        alerts = [
            {
                "name": "backend_5xx_errors",
                "description": "최근 5분 안에 HTTP 5xx 응답이 발생했습니다.",
                "sql": f'SELECT count(*) AS error_count FROM "{stream}" WHERE event = \'http_request\' AND status_code >= 500 HAVING count(*) >= 1',
                "period": 5, "frequency": 1, "operator": ">=", "threshold": 1,
                "silence": 10, "row_template": "최근 5분 5xx 오류: {error_count}건",
            },
            {
                "name": "backend_unhandled_errors",
                "description": "처리되지 않은 애플리케이션 오류가 발생했습니다.",
                "sql": f'SELECT logger, message, count(*) AS error_count FROM "{stream}" WHERE level = \'error\' GROUP BY logger, message',
                "period": 5, "frequency": 1, "operator": ">=", "threshold": 1,
                "silence": 10, "row_template": "{logger}: {message} ({error_count}건)",
            },
            {
                "name": "backend_slow_requests",
                "description": "2초 이상 걸린 요청이 반복되었습니다.",
                "sql": f'SELECT path, count(*) AS request_count, max(duration_ms) AS max_duration_ms FROM "{stream}" WHERE event = \'http_request\' AND duration_ms >= 2000 GROUP BY path HAVING count(*) >= 3',
                "period": 10, "frequency": 5, "operator": ">=", "threshold": 1,
                "silence": 30, "row_template": "{path}: 최대 {max_duration_ms}ms ({request_count}건)",
            },
            {
                "name": "backend_heartbeat_missing",
                "description": "최근 3분 동안 백엔드 heartbeat가 없습니다.",
                "sql": f'SELECT count(*) AS heartbeat_count FROM "{stream}" WHERE event = \'heartbeat\' HAVING count(*) < 1',
                "period": 3, "frequency": 1, "operator": ">=", "threshold": 1,
                "silence": 10, "row_template": "최근 3분 heartbeat: {heartbeat_count}건",
            },
            {
                "name": "container_service_down",
                "description": "애플리케이션 컨테이너의 HTTP 상태 점검이 실패했습니다.",
                "sql": f'SELECT target_service, status_code FROM "{stream}" WHERE event = \'service_health\' AND status = \'down\'',
                "period": 2, "frequency": 1, "operator": ">=", "threshold": 1,
                "silence": 5, "row_template": "{target_service} 응답 실패 (HTTP {status_code})",
            },
        ]
        for alert in alerts:
            is_real_time = alert.get("is_real_time", False)
            current = existing_by_name.get(alert["name"])
            if current:
                self._request(
                    "DELETE",
                    f"/api/v2/{org}/alerts/{current['alert_id']}",
                )
            query_condition = (
                {"type": "custom", "conditions": alert["conditions"]}
                if is_real_time
                else {"type": "sql", "sql": alert["sql"]}
            )
            payload = {
                "name": alert["name"],
                "description": alert["description"],
                "stream_type": "logs",
                "stream_name": stream,
                "is_real_time": is_real_time,
                "query_condition": query_condition,
                "trigger_condition": {
                    "period": alert["period"],
                    "operator": alert["operator"],
                    "threshold": alert["threshold"],
                    "frequency": alert["frequency"],
                    "frequency_type": "minutes",
                    "silence": alert["silence"],
                },
                "destinations": ["discord_alerts"],
                "enabled": True,
                "notify_on_recovery": True,
                "row_template": alert["row_template"],
                "row_template_type": "String",
            }
            self._request("POST", f"/api/v2/{org}/alerts", payload)
        self.stdout.write(self.style.SUCCESS("OpenObserve Discord destination과 기본 알림 구성이 완료됐습니다."))
