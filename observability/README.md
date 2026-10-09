# OpenObserve 운영 설정

OpenObserve는 `docker compose up -d --build`로 애플리케이션과 함께 시작되며
`http://localhost:5080`에서 사용할 수 있습니다. 로그인 정보는 저장소 루트의
`.env`에 있는 `OPENOBSERVE_USER`, `OPENOBSERVE_PASSWORD`입니다.
기본 바인딩은 `127.0.0.1`이므로 같은 PC에서만 접속할 수 있습니다. 계정을 여러
사람에게 공유하지 말고 OpenObserve에서 사용자별 계정과 최소 권한을 부여하세요.

백엔드는 `blog_logs` 스트림에 다음 이벤트를 비동기로 보냅니다.

- `http_request`: 경로, 메서드, 상태 코드, 응답 시간, 요청 ID
- `request_error`: 처리되지 않은 요청 예외
- `heartbeat`: 30초 간격의 백엔드 생존 신호
- `service_health`: backend, WAF, 두 프론트엔드, OpenObserve의 개별 HTTP 상태
- `waf_detection`: OWASP CRS 규칙, 공격 유형, 심각도, 경로
- Django 애플리케이션의 일반 warning/error 로그

Authorization, Cookie와 전체 요청 본문은 OpenObserve에 수집하지 않습니다. WAF 이벤트에는
차단을 위한 원본 IP와 최대 300자의 탐지 조각을 보관하되 민감 필드 값은 제거합니다. 전송 실패나
큐 포화는 웹 요청을 지연시키지 않습니다. 데이터 기본 보존 기간은 14일입니다.

## WAF와 페이로드 검사

외부의 `localhost:8000`은 Django가 아니라 `waf` 컨테이너를 가리킵니다. Django는
Compose 내부 네트워크에만 노출됩니다. WAF는 요청 본문을 메모리에서 검사하지만
감사 로그는 `A/H/Z` 부분만 기록하므로 요청 본문, Cookie, Authorization 헤더를
저장하지 않습니다. 감사 로그에서 필요한 탐지 정보만
[`security-event.schema.json`](./security-event.schema.json) 형식으로 정규화해
OpenObserve로 전송합니다.

초기값은 `.env`의 `WAF_MODE=DetectionOnly`입니다. 최소 며칠간 오탐을 검토하고
필요한 예외만 `waf/REQUEST-900-EXCLUSION-RULES-BEFORE-CRS.conf`에 규칙 단위로
추가한 뒤 `WAF_MODE=On`으로 변경하세요. 엔진을 자체 WAF로 교체할 때도 이 JSON
계약만 출력하면 기존 대시보드와 Discord 알림을 그대로 쓸 수 있습니다.

## 자동 Discord 알림 구성

`.env`에 `DISCORD_ALERT_WEBHOOK_URL`이 설정되어 있으면 백엔드 시작 시 다음
항목을 멱등적으로 생성합니다.

- `discord_incident` 템플릿
- `discord_alerts` Webhook destination
- 5xx, 처리되지 않은 예외, 반복되는 느린 요청, heartbeat 누락 및 개별 컨테이너 장애 알림
- WAF 수집기에서 즉시 전송하는 Discord 탐지 알림(기본 중복 방지 60초)
- 각 알림의 10~30분 cooldown과 복구 알림

웹훅이 아직 설정되지 않은 경우 로그 수집은 정상 동작하고 알림 구성만
건너뜁니다. 아래 내용은 OpenObserve UI에서 구성을 확인하거나 수동 복구할 때
사용할 기준값입니다.

## Discord Destination

OpenObserve에서 **Management → Templates**에 `discord_incident` 템플릿을 만들고
다음 JSON을 본문으로 등록합니다.

```json
{
  "username": "SECOVATE200 Monitor",
  "allowed_mentions": {"parse": []},
  "content": "🚨 **{alert_name}**\n환경: {org_name}\n스트림: {stream_name}\n{rows}"
}
```

**Management → Destinations**에서 Webhook 목적지 `discord_alerts`를 만듭니다.

- URL: `.env`의 `DISCORD_ALERT_WEBHOOK_URL`
- Method: `POST`
- Header: `Content-Type: application/json`
- Template: `discord_incident`

## 권장 Alert

모두 stream type `logs`, stream `blog_logs`, destination `discord_alerts`, recovery
notification 활성화로 생성합니다.

### 5xx 오류

```sql
SELECT count(*) AS error_count
FROM "blog_logs"
WHERE event = 'http_request' AND status_code >= 500
```

- 주기/조회 범위: 1분/5분
- 조건: `error_count >= 1`
- cooldown: 10분
- row template: `최근 5분 5xx 오류: {error_count}건`

### 처리되지 않은 예외

```sql
SELECT logger, message, count(*) AS error_count
FROM "blog_logs"
WHERE level = 'error'
GROUP BY logger, message
ORDER BY error_count DESC
LIMIT 10
```

- 주기/조회 범위: 1분/5분
- 조건: `error_count >= 1`
- cooldown: 10분
- row template: `{logger}: {message} ({error_count}건)`

### 느린 요청

```sql
SELECT path, count(*) AS request_count, max(duration_ms) AS max_duration_ms
FROM "blog_logs"
WHERE event = 'http_request' AND duration_ms >= 2000
GROUP BY path
ORDER BY max_duration_ms DESC
```

- 주기/조회 범위: 5분/10분
- 조건: `request_count >= 3`
- cooldown: 30분
- row template: `{path}: 최대 {max_duration_ms}ms ({request_count}건)`

### Heartbeat 누락

```sql
SELECT count(*) AS heartbeat_count
FROM "blog_logs"
WHERE event = 'heartbeat'
HAVING count(*) < 1
```

- 주기/조회 범위: 1분/3분
- 조건: 결과 행 개수 `>= 1`
- cooldown: 10분
- 복구 알림 활성화

### WAF 공격 탐지(즉시)

```sql
SELECT severity, attack_type, rule_id, path, count(*) AS error_count
FROM "blog_logs"
WHERE event = 'waf_detection'
GROUP BY severity, attack_type, rule_id, path
ORDER BY error_count DESC
```

- 조건: ModSecurity 감사 로그에 새 탐지 트랜잭션 생성
- 처리: OpenObserve 적재와 Discord 전송을 함께 수행
- 기록: 차단에 사용할 원본 IP와 WAF가 실제 매칭한 최대 300자의 탐지 조각
- 보호: 비밀번호·토큰·쿠키·Authorization 등 민감 필드의 탐지값은 자동 제거
- 중복 방지: 동일 클라이언트 지문·경로·공격 유형 기준 기본 60초

## 권장 Dashboard 패널

새 대시보드 `Blog Operations`를 만들고 아래 SQL을 패널별로 등록합니다.

### 상태 코드별 요청량

```sql
SELECT histogram(_timestamp, '5 minute') AS time,
       status_code,
       count(*) AS requests
FROM "blog_logs"
WHERE event = 'http_request'
GROUP BY time, status_code
ORDER BY time
```

### 평균·최대 응답 시간

```sql
SELECT histogram(_timestamp, '5 minute') AS time,
       avg(duration_ms) AS average_ms,
       max(duration_ms) AS maximum_ms
FROM "blog_logs"
WHERE event = 'http_request'
GROUP BY time
ORDER BY time
```

### 오류가 많은 경로

```sql
SELECT path, count(*) AS errors
FROM "blog_logs"
WHERE event = 'http_request' AND status_code >= 400
GROUP BY path
ORDER BY errors DESC
LIMIT 10
```

### 최근 예외

```sql
SELECT _timestamp, logger, message, exception, request_id
FROM "blog_logs"
WHERE level = 'error'
ORDER BY _timestamp DESC
LIMIT 50
```

### 공격 유형별 탐지량

```sql
SELECT histogram(_timestamp, '5 minute') AS time,
       attack_type,
       count(*) AS detections
FROM "blog_logs"
WHERE event = 'waf_detection'
GROUP BY time, attack_type
ORDER BY time
```

운영 배포에서는 5080 포트를 인터넷에 직접 노출하지 말고 VPN, SSH 터널 또는
인증 프록시 뒤에서만 접근합니다. `OPENOBSERVE_BIND_ADDRESS`를 `0.0.0.0`으로
바꾸는 것만으로 외부 공개하지 않습니다.
