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


class Command(BaseCommand):
    help = "ModSecurity JSON 감사 로그를 안전한 공통 보안 이벤트로 변환합니다."

    def add_arguments(self, parser):
        parser.add_argument("--path", default="/var/log/waf/audit/audit.json")

    def handle(self, *args, **options):
        path = options["path"]
        last_sent = {}
        while True:
            if not os.path.exists(path):
                time.sleep(2)
                continue
            with open(path, encoding="utf-8", errors="replace") as audit_log:
                audit_log.seek(0, os.SEEK_END)
                while True:
                    line = audit_log.readline()
                    if not line:
                        if not os.path.exists(path) or os.path.getsize(path) < audit_log.tell():
                            break
                        time.sleep(1)
                        continue
                    try:
                        document = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    events = normalize_waf_audit(document)
                    for event in events:
                        logger.warning(
                            "WAF detection rule=%s type=%s path=%s",
                            event["rule_id"], event["attack_type"], event["path"],
                            extra=event,
                        )
                    if events:
                        key = (
                            events[0]["client_fingerprint"],
                            events[0]["path"],
                            tuple(sorted({event["attack_type"] for event in events})),
                        )
                        now = time.monotonic()
                        cooldown = settings.WAF_DISCORD_COOLDOWN_SECONDS
                        if now - last_sent.get(key, float("-inf")) >= cooldown:
                            if send_discord_alert(events):
                                last_sent[key] = now
                                logger.info(
                                    "WAF Discord alert sent request_id=%s",
                                    events[0]["request_id"],
                                    extra={
                                        "event": "waf_discord_alert",
                                        "request_id": events[0]["request_id"],
                                        "path": events[0]["path"],
                                        "status": "sent",
                                    },
                                )
