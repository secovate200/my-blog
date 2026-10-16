import json
import logging
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.management.base import BaseCommand

from config.waf_events import normalize_waf_audit


logger = logging.getLogger("security.waf")

# 950100은 공격 시그니처가 아니라 백엔드의 5xx 응답을 알리는 상태 규칙입니다.
# 원본 이벤트는 장애 분석을 위해 OpenObserve에 남기되 공격 Discord 알림에서는 제외합니다.
NON_ATTACK_RULE_IDS = frozenset({"950100"})


def _wait(stop_event, seconds):
    """통합 에이전트 종료 신호가 있으면 대기 중에도 즉시 빠져나옵니다."""

    if stop_event is None:
        time.sleep(seconds)
        return False
    return stop_event.wait(seconds)


def send_discord_alert(events):
    if not events or not settings.DISCORD_ALERT_WEBHOOK_URL:
        return False
    first = events[0]
    attack_types = sorted({event["attack_type"] for event in events})
    rule_ids = sorted({event["rule_id"] for event in events if event["rule_id"] != "949110"})
    matched = []
    for event in events:
        value = event.get("matched_data")
        if value and value not in matched:
            matched.append(value.replace("`", "'").replace("\n", " ")[:160])
    content = (
        "🚨 **WAF 공격 탐지**\n"
        f"처리: **{first['action']}** / 상태: `{first['status_code']}`\n"
        f"요청: `{first['method']} {first['path']}`\n"
        f"공격 IP: `{first['client_ip']}`\n"
        f"유형: `{', '.join(attack_types)}`\n"
        f"규칙: `{', '.join(rule_ids[:12])}`\n"
    )
    if matched:
        content += f"탐지값: `{' | '.join(matched[:3])}`\n"
    content += f"요청 ID: `{first['request_id']}`"
    request = Request(
        settings.DISCORD_ALERT_WEBHOOK_URL,
        data=json.dumps({
            "username": "SECOVATE200 WAF",
            "allowed_mentions": {"parse": []},
            "content": content,
        }, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "SECOVATE200-WAF/1.0"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=5) as response:
            return response.status in (200, 204)
    except (HTTPError, URLError, TimeoutError, OSError):
        return False


def export_waf_events(path, stop_event=None):
    """WAF 감사 로그를 추적해 OpenObserve와 Discord용 이벤트로 변환합니다."""

    last_sent = {}
    logger.info("WAF 감사 로그 전달을 시작합니다. 경로=%s", path)
    while stop_event is None or not stop_event.is_set():
        if not os.path.exists(path):
            if _wait(stop_event, 2):
                return
            continue
        with open(path, encoding="utf-8", errors="replace") as audit_log:
            audit_log.seek(0, os.SEEK_END)
            while stop_event is None or not stop_event.is_set():
                line = audit_log.readline()
                if not line:
                    if not os.path.exists(path) or os.path.getsize(path) < audit_log.tell():
                        break
                    if _wait(stop_event, 1):
                        return
                    continue
                try:
                    document = json.loads(line)
                except json.JSONDecodeError:
                    continue
                events = normalize_waf_audit(document)
                for event in events:
                    if event["rule_id"] in NON_ATTACK_RULE_IDS:
                        logger.info(
                            "WAF가 서버 오류 응답을 관측했습니다: 규칙=%s, 상태=%s, 경로=%s",
                            event["rule_id"], event["status_code"], event["path"],
                            extra=event,
                        )
                    else:
                        logger.warning(
                            "WAF 공격 탐지: 규칙=%s, 유형=%s, 경로=%s",
                            event["rule_id"], event["attack_type"], event["path"],
                            extra=event,
                        )

                # 서버 오류는 상태 감시에서 다루므로 공격으로 분류할 수 있는 이벤트만 알립니다.
                alert_events = [
                    event for event in events
                    if event["rule_id"] not in NON_ATTACK_RULE_IDS
                ]
                if alert_events:
                    key = (
                        alert_events[0]["client_fingerprint"],
                        alert_events[0]["path"],
                        tuple(sorted({event["attack_type"] for event in alert_events})),
                    )
                    now = time.monotonic()
                    cooldown = settings.WAF_DISCORD_COOLDOWN_SECONDS
                    if now - last_sent.get(key, float("-inf")) >= cooldown:
                        if send_discord_alert(alert_events):
                            last_sent[key] = now
                            logger.info(
                                "WAF Discord 알림을 발송했습니다. 요청 ID=%s",
                                alert_events[0]["request_id"],
                                extra={
                                    "event": "waf_discord_alert",
                                    "request_id": alert_events[0]["request_id"],
                                    "path": alert_events[0]["path"],
                                    "status": "sent",
                                },
                            )


class Command(BaseCommand):
    help = "ModSecurity JSON 감사 로그를 안전한 공통 보안 이벤트로 변환합니다."

    def add_arguments(self, parser):
        parser.add_argument("--path", default="/var/log/waf/audit/audit.json")

    def handle(self, *args, **options):
        export_waf_events(options["path"])
