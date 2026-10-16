# 운영 배포 체크리스트

이 문서는 Docker Compose 운영 이미지를 안전하게 시작하기 전에 반드시 확인할 항목을 정리합니다.
현재 구성은 TLS를 직접 종료하지 않으므로 Cloudflare, 로드 밸런서, Caddy 같은 HTTPS 프록시가
블로그 컨테이너 앞에 있어야 합니다.

## 1. 환경 변수 준비

`.env.example`을 참고해 서버의 `.env`를 작성합니다. 다음 값은 예시 값을 그대로 사용하면 안 됩니다.

- `DJANGO_SECRET_KEY`: `python -c "import secrets; print(secrets.token_urlsafe(64))"`로 생성합니다.
- `OPENOBSERVE_PASSWORD`: 다른 서비스에서 사용하지 않는 강한 비밀번호를 사용합니다.
- Discord 및 SMTP 자격 증명: 운영 계정 전용 값을 사용합니다.
- 모든 `example.com` 주소: 실제 HTTPS 도메인으로 변경합니다.

`DJANGO_ALLOWED_HOSTS`에는 호스트 이름만 넣고, `DJANGO_CSRF_TRUSTED_ORIGINS`에는
`https://`를 포함한 대시보드 원본 주소를 넣습니다.

## 2. TLS와 관리자 접근 범위 확인

- 공개 블로그만 인터넷에 노출합니다.
- 대시보드는 기본값인 `127.0.0.1:5175`를 유지하고 VPN 또는 SSH 터널로 접근합니다.
- WAF 진단 포트 `8000`과 OpenObserve `5080`도 루프백 바인딩을 유지합니다.
- TLS 프록시는 원래 프로토콜을 `X-Forwarded-Proto: https`로 전달해야 합니다.
- 모든 서브도메인이 HTTPS로 준비되기 전에는 HSTS preload를 활성화하지 않습니다.

## 3. 기존 데이터 이전

운영 Compose는 DB와 업로드 파일을 이미지가 아닌 `backend-data`, `backend-media` 볼륨에 저장합니다.
기존 `backend/db.sqlite3`와 `backend/media`는 자동으로 복사되지 않으므로 첫 실행 전에 별도로
백업하고 운영 볼륨으로 이전해야 합니다. 원본을 보존한 상태에서 이전 후 게시글과 첨부파일을
확인하기 전에는 기존 파일을 삭제하지 않습니다.

## 4. 배포 전 검사

```powershell
docker compose config --quiet
docker compose build
docker compose run --rm backend python manage.py check --deploy
docker compose run --rm backend python manage.py test
```

검사가 끝나면 다음 명령으로 시작합니다.

```powershell
docker compose up -d
docker compose ps
docker compose logs --tail 100 backend waf blog-front dashboard-front observability-agent
```

## 5. 배포 직후 확인

- 공개 블로그의 목록·상세·문의 기능이 정상 동작하는지 확인합니다.
- VPN 또는 터널을 통해 대시보드와 Django Admin에 로그인합니다.
- 세션 쿠키와 CSRF 쿠키에 `Secure`가 표시되는지 브라우저 개발자 도구에서 확인합니다.
- HTTP 요청이 HTTPS로 전환되는지 확인합니다.
- WAF와 OpenObserve 로그가 한글 메시지로 수집되는지 확인합니다.
- DB와 업로드 볼륨의 정기 백업을 설정합니다.

저장형 XSS P1 두 건은 요청에 따라 이번 배포 준비에서 수정하지 않았습니다. 개인 스테이징에서만
진단하고, 외부 공개 전에 반드시 수정 및 재검증해야 합니다.
