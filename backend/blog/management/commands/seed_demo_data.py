from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from blog.models import Category, Post, Project, ProjectMember, ProjectPost, Tag


POSTS = (
    (
        "Web Security",
        "접근 제어 취약점을 점검하는 실전 체크리스트",
        "인증된 사용자라도 다른 사용자의 리소스에 접근할 수 있는지 확인하는 절차를 정리했습니다. 객체 식별자 변경, 역할별 권한 비교, 서버 측 검증 여부를 차례로 점검합니다.",
        ("Access Control", "OWASP"),
    ),
    (
        "Bug Bounty",
        "재현 가능한 버그바운티 리포트 작성법",
        "담당자가 같은 결과를 빠르게 확인할 수 있도록 환경, 재현 단계, 기대 결과와 실제 결과, 영향도를 구성하는 방법을 예시와 함께 소개합니다.",
        ("Report", "Methodology"),
    ),
    (
        "Development",
        "React 블로그에 다크 모드를 적용하며 배운 것들",
        "CSS 변수로 색상 토큰을 분리하고 시스템 설정과 사용자의 선택을 함께 반영한 다크 모드 구현 과정을 기록합니다.",
        ("React", "CSS"),
    ),
    (
        "Web Security",
        "CORS 설정에서 자주 놓치는 보안 항목",
        "Origin 검증, 자격 증명 허용, 프리플라이트 응답을 중심으로 CORS 설정을 안전하게 점검하는 기준을 정리했습니다.",
        ("CORS", "Browser"),
    ),
    (
        "Development",
        "Vite 기반 React 프로젝트 구조 잡기",
        "화면 단위 컨테이너와 재사용 컴포넌트, 공통 스타일을 분리해 작은 프로젝트가 커져도 관리하기 쉬운 구조를 만듭니다.",
        ("Vite", "React"),
    ),
    (
        "Lab",
        "Docker로 로컬 보안 테스트 환경 구성하기",
        "테스트 대상과 분석 도구를 격리된 네트워크에 배치해 웹 취약점을 안전하고 반복 가능하게 실습하는 환경을 구성합니다.",
        ("Docker", "Lab"),
    ),
)

PROJECTS = (
    {
        "title": "Web Security Lab",
        "description": "격리된 Docker 환경에서 웹 보안 취약점을 재현하고 공격 조건과 방어 방법을 함께 문서화하는 프로젝트입니다.",
        "is_public": True,
        "display_order": 1,
        "posts": (
            ("로컬 보안 테스트 환경 구성", "Docker 네트워크를 분리하고 테스트 대상과 분석 도구를 안전하게 연결한 과정을 정리했습니다.", ("Docker", "Lab")),
            ("접근 제어 테스트 시나리오 설계", "권한별 계정을 기준으로 객체와 기능 수준의 접근 제어를 확인하는 시나리오를 구성했습니다.", ("Access Control", "OWASP")),
        ),
    },
    {
        "title": "Personal Blog",
        "description": "React와 Vite로 만든 개인 기술 블로그입니다. 반응형 레이아웃과 다크 모드, 카테고리 및 태그 필터를 구현합니다.",
        "is_public": True,
        "display_order": 2,
        "posts": (
            ("확장 가능한 React 프로젝트 구조", "화면 단위 컨테이너와 재사용 컴포넌트를 분리하며 적용한 구조와 기준을 소개합니다.", ("React", "Architecture")),
            ("CSS 변수로 다크 모드 구현하기", "색상 토큰을 분리해 하나의 컴포넌트가 두 테마에서 자연스럽게 보이도록 개선했습니다.", ("CSS", "Dark Mode")),
            ("카테고리와 태그 필터 연결", "URL 쿼리와 게시글 목록을 동기화해 공유 가능한 필터를 구현한 과정을 기록했습니다.", ("React", "UX")),
        ),
    },
    {
        "title": "Recon Toolkit",
        "description": "여러 출처에서 수집한 서브도메인과 서비스 정보를 정규화하고 검증하는 반복 작업을 자동화하는 도구 모음입니다.",
        "is_public": False,
        "display_order": 3,
        "posts": (
            ("서브도메인 정찰 파이프라인 만들기", "수집부터 중복 제거와 응답 검증까지 이어지는 작업을 작은 단계로 나누어 자동화했습니다.", ("Recon", "Automation")),
            ("정찰 결과를 재사용 가능한 데이터로 정리하기", "도구마다 다른 출력 형식을 정규화해 이후 점검에서 다시 활용할 수 있게 저장합니다.", ("Data", "Workflow")),
        ),
    },
)


class Command(BaseCommand):
    help = "개발 및 화면 확인용 블로그 더미 데이터를 중복 없이 생성합니다."

    @transaction.atomic
    def handle(self, *args, **options):
        user_model = get_user_model()
        author = user_model.objects.filter(is_superuser=True).order_by("id").first()

        if author is None:
            author, created = user_model.objects.get_or_create(
                username="demo_admin",
                defaults={"is_staff": True, "is_superuser": True},
            )
            if created:
                author.set_unusable_password()
                author.save(update_fields=("password",))
                self.stdout.write("로그인 불가능한 demo_admin 작성자 계정을 생성했습니다.")

        tag_cache = {}

        def tags_for(names):
            tags = []
            for name in names:
                if name not in tag_cache:
                    tag_cache[name], _ = Tag.objects.get_or_create(name=name)
                tags.append(tag_cache[name])
            return tags

        for category_name, title, content, tag_names in POSTS:
            category, _ = Category.objects.get_or_create(name=category_name)
            post, _ = Post.objects.update_or_create(
                title=title,
                defaults={
                    "author": author,
                    "category": category,
                    "content": content,
                    "status": Post.Status.PUBLISHED,
                },
            )
            post.tags.set(tags_for(tag_names))

        for project_data in PROJECTS:
            project, _ = Project.objects.update_or_create(
                title=project_data["title"],
                defaults={
                    "description": project_data["description"],
                    "is_public": project_data["is_public"],
                    "display_order": project_data["display_order"],
                },
            )
            ProjectMember.objects.get_or_create(
                project=project,
                user=author,
                defaults={"granted_by": author},
            )
            for title, content, tag_names in project_data["posts"]:
                project_post, _ = ProjectPost.objects.update_or_create(
                    project=project,
                    title=title,
                    defaults={
                        "author": author,
                        "content": content,
                        "is_public": project_data["is_public"],
                    },
                )
                project_post.tags.set(tags_for(tag_names))

        self.stdout.write(
            self.style.SUCCESS(
                f"더미 데이터 생성 완료: 게시글 {len(POSTS)}개, "
                f"프로젝트 {len(PROJECTS)}개, 프로젝트 글 "
                f"{sum(len(project['posts']) for project in PROJECTS)}개"
            )
        )
