"""UC-01 공개 게시글 목록 유즈케이스를 반복 가능한 방식으로 자동 검증합니다."""

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.test import Client
from django.urls import reverse

from blog.models import Post


class Command(BaseCommand):
    help = "UC-01의 목록, 페이지네이션, 정렬, 초안 비노출과 빈 결과를 자동 검증합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-seed",
            action="store_true",
            help="유즈케이스 테스트 데이터 구성을 생략합니다.",
        )

    def handle(self, *args, **options):
        if not options["skip_seed"]:
            # 매번 같은 기준 데이터에서 시작해야 이전 수동 테스트가 자동화 결과에
            # 영향을 주지 않으므로 멱등적인 시드 명령을 먼저 실행합니다.
            call_command("seed_use_case_data", verbosity=0)

        # 운영과 동일한 허용 호스트를 사용해야 ALLOWED_HOSTS 검증까지 통과한
        # 실제 응답을 검사할 수 있습니다. Django의 기본 testserver는 이 프로젝트의
        # 허용 목록에 의도적으로 포함하지 않습니다.
        client = Client(HTTP_HOST="localhost")
        endpoint = reverse("blog:post-list")
        checks = []

        first = client.get(endpoint, {"category": "Use Case Test"})
        self._check(checks, "첫 페이지 HTTP 200", first.status_code == 200)
        first_data = first.json() if first.status_code == 200 else {}
        self._check(checks, "공개 게시글 총 12개", first_data.get("count") == 12)
        self._check(
            checks,
            "첫 페이지에 10개 표시",
            len(first_data.get("results", [])) == 10,
        )
        self._check(checks, "다음 페이지 링크 제공", bool(first_data.get("next")))
        self._check(checks, "첫 페이지에는 이전 링크 없음", first_data.get("previous") is None)

        second = client.get(endpoint, {"category": "Use Case Test", "page": 2})
        self._check(checks, "두 번째 페이지 HTTP 200", second.status_code == 200)
        second_data = second.json() if second.status_code == 200 else {}
        self._check(
            checks,
            "두 번째 페이지에 나머지 2개 표시",
            len(second_data.get("results", [])) == 2,
        )
        self._check(checks, "마지막 페이지에는 다음 링크 없음", second_data.get("next") is None)
        self._check(checks, "두 번째 페이지에 이전 링크 제공", bool(second_data.get("previous")))

        first_ids = [item["id"] for item in first_data.get("results", [])]
        second_ids = [item["id"] for item in second_data.get("results", [])]
        self._check(checks, "페이지 간 게시글 중복 없음", not set(first_ids) & set(second_ids))
        self._check(checks, "두 페이지를 합치면 12개", len(first_ids + second_ids) == 12)

        titles = [item["title"] for item in first_data.get("results", [])]
        expected_titles = [
            f"[UC-01] 공개 목록 점검 게시글 {number:02d}"
            for number in range(12, 2, -1)
        ]
        self._check(checks, "최신 작성순 정렬", titles == expected_titles)

        draft = Post.objects.get(title="[UC-09] 권한 없는 사용자에게 보이면 안 되는 초안")
        draft_search = client.get(endpoint, {"q": "권한 없는 사용자에게 보이면 안 되는 초안"})
        draft_detail = client.get(reverse("blog:post-detail", args=[draft.pk]))
        self._check(checks, "초안 검색 결과 비노출", draft_search.json().get("count") == 0)
        self._check(checks, "초안 상세 조회 404", draft_detail.status_code == 404)

        empty = client.get(endpoint, {"q": "UC01_AUTOMATION_NO_RESULT_9F21"})
        self._check(checks, "검색 결과 없음 응답", empty.status_code == 200 and empty.json().get("count") == 0)

        failed = [name for name, passed in checks if not passed]
        self.stdout.write("")
        self.stdout.write(f"UC-01 자동 테스트 결과: {len(checks) - len(failed)}/{len(checks)} 통과")
        if failed:
            raise CommandError("UC-01 실패 항목: " + ", ".join(failed))
        self.stdout.write(self.style.SUCCESS("UC-01 최종 판정: 통과"))

    def _check(self, checks, name, passed):
        checks.append((name, passed))
        marker = "통과" if passed else "실패"
        style = self.style.SUCCESS if passed else self.style.ERROR
        self.stdout.write(style(f"[{marker}] {name}"))
