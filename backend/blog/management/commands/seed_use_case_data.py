"""UC-01~UC-15를 수동·통합 테스트할 수 있는 개발 데이터를 구성합니다."""

import base64
import json
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from blog.models import (
    BlogAsset,
    Category,
    ContactMessage,
    Post,
    Project,
    ProjectMember,
    ProjectPost,
    Tag,
    UserAccessStatus,
)


TEST_PASSWORD = "UseCase!2026"
IMAGE_ASSET_ID = uuid.UUID("10000000-0000-4000-8000-000000000003")
FILE_ASSET_ID = uuid.UUID("10000000-0000-4000-8000-000000000012")
ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)

TEST_USERS = {
    "uc_admin": {
        "email": "uc-admin@example.com",
        "first_name": "유즈케이스 최고 관리자",
        "is_staff": True,
        "is_superuser": True,
        "status": UserAccessStatus.Status.APPROVED,
    },
    "uc_editor": {
        "email": "uc-editor@example.com",
        "first_name": "게시글 편집자",
        "is_staff": True,
        "is_superuser": False,
        "status": UserAccessStatus.Status.APPROVED,
    },
    "uc_viewer": {
        "email": "uc-viewer@example.com",
        "first_name": "일반 조회 사용자",
        "is_staff": False,
        "is_superuser": False,
        "status": UserAccessStatus.Status.APPROVED,
    },
    "uc_member": {
        "email": "uc-member@example.com",
        "first_name": "프로젝트 구성원",
        "is_staff": False,
        "is_superuser": False,
        "status": UserAccessStatus.Status.APPROVED,
    },
    "uc_pending": {
        "email": "uc-pending@example.com",
        "first_name": "승인 대기 사용자",
        "is_staff": False,
        "is_superuser": False,
        "status": UserAccessStatus.Status.PENDING,
    },
    "uc_banned": {
        "email": "uc-banned@example.com",
        "first_name": "차단 사용자",
        "is_staff": False,
        "is_superuser": False,
        "status": UserAccessStatus.Status.BANNED,
        "ban_reason": "유즈케이스 차단 안내 확인용 계정입니다.",
    },
}


class Command(BaseCommand):
    help = "UC-01~UC-15 테스트에 필요한 계정, 권한, 콘텐츠와 문의 데이터를 구성합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="DEBUG가 꺼진 환경에서도 테스트 데이터를 생성합니다.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "운영 환경의 데이터 오염을 막기 위해 실행을 중단했습니다. "
                "의도한 작업이면 --force 옵션을 사용하세요."
            )

        users = self._seed_users()
        categories = self._seed_categories()
        assets = self._seed_assets(users["uc_admin"])
        self._seed_posts(users, categories, assets)
        self._seed_projects(users)
        self._seed_contacts(users["uc_admin"])

        self.stdout.write(self.style.SUCCESS("유즈케이스 테스트 데이터 구성이 완료되었습니다."))
        self.stdout.write(f"공통 비밀번호: {TEST_PASSWORD}")
        self.stdout.write("계정: " + ", ".join(TEST_USERS))
        self.stdout.write("UC-03 게시글 경로: /post/55003")

    def _seed_users(self):
        """승인·대기·차단과 역할별 권한을 재현하는 전용 계정을 만듭니다."""

        user_model = get_user_model()
        users = {}
        for username, user_data in TEST_USERS.items():
            status = user_data["status"]
            user, _ = user_model.objects.update_or_create(
                username=username,
                defaults={
                    "email": user_data["email"],
                    "first_name": user_data["first_name"],
                    "is_staff": user_data["is_staff"],
                    "is_superuser": user_data["is_superuser"],
                    "is_active": status == UserAccessStatus.Status.APPROVED,
                },
            )
            # 테스트 문서에 적힌 하나의 비밀번호로 언제든 환경을 재현할 수 있어야
            # DB를 다시 만들거나 명령을 재실행해도 로그인 절차가 달라지지 않습니다.
            user.set_password(TEST_PASSWORD)
            user.save(update_fields=("password",))
            UserAccessStatus.objects.update_or_create(
                user=user,
                defaults={
                    "status": status,
                    "ban_reason": user_data.get("ban_reason", ""),
                    "reviewed_by": None,
                    "reviewed_at": None,
                },
            )
            users[username] = user

        editor_permissions = Permission.objects.filter(
            content_type__app_label="blog",
            codename__in=("add_post", "change_post", "delete_post", "view_post"),
        )
        users["uc_editor"].user_permissions.set(editor_permissions)
        users["uc_viewer"].user_permissions.set(
            Permission.objects.filter(
                content_type__app_label="blog", codename="view_post"
            )
        )
        return users

    @staticmethod
    def _seed_categories():
        return {
            name: Category.objects.get_or_create(name=name)[0]
            for name in ("Development", "Web Security", "Use Case Test")
        }

    @staticmethod
    def _ensure_asset(*, asset_id, user, name, content_type, kind, content):
        asset, _ = BlogAsset.objects.get_or_create(
            pk=asset_id,
            defaults={
                "original_name": name,
                "content_type": content_type,
                "size": len(content),
                "kind": kind,
                "uploaded_by": user,
            },
        )
        # DB만 복원되고 미디어 볼륨이 비어 있는 상황도 반복 테스트에서 흔하므로,
        # 레코드가 존재하더라도 실파일이 없으면 같은 내용으로 다시 생성합니다.
        if not asset.file or not asset.file.storage.exists(asset.file.name):
            asset.file.save(name, ContentFile(content), save=False)
            asset.original_name = name
            asset.content_type = content_type
            asset.size = len(content)
            asset.kind = kind
            asset.uploaded_by = user
            asset.save()
        return asset

    def _seed_assets(self, admin):
        return {
            "image": self._ensure_asset(
                asset_id=IMAGE_ASSET_ID,
                user=admin,
                name="uc-03-detail-image.png",
                content_type="image/png",
                kind=BlogAsset.Kind.IMAGE,
                content=ONE_PIXEL_PNG,
            ),
            "file": self._ensure_asset(
                asset_id=FILE_ASSET_ID,
                user=admin,
                name="uc-12-attachment.txt",
                content_type="text/plain",
                kind=BlogAsset.Kind.FILE,
                content="UC-12 첨부파일 다운로드 테스트입니다.\n".encode(),
            ),
        }

    @staticmethod
    def _set_tags(instance, names):
        instance.tags.set([Tag.objects.get_or_create(name=name)[0] for name in names])

    def _seed_posts(self, users, categories, assets):
        """페이지네이션, 권한, 상세 블록 렌더링에 필요한 글을 구성합니다."""

        for number in range(1, 13):
            post, _ = Post.objects.update_or_create(
                title=f"[UC-01] 공개 목록 점검 게시글 {number:02d}",
                defaults={
                    "author": users["uc_admin"],
                    "category": categories["Use Case Test"],
                    "content": f"페이지 이동과 정렬을 확인하는 {number}번째 공개 글입니다.",
                    "status": Post.Status.PUBLISHED,
                },
            )
            self._set_tags(post, ("UC-01", "페이지네이션"))

        draft, _ = Post.objects.update_or_create(
            title="[UC-09] 권한 없는 사용자에게 보이면 안 되는 초안",
            defaults={
                "author": users["uc_editor"],
                "category": categories["Use Case Test"],
                "content": "공개 API와 초안 조회 권한을 점검하기 위한 글입니다.",
                "status": Post.Status.DRAFT,
            },
        )
        self._set_tags(draft, ("UC-09", "초안"))

        image = assets["image"]
        attachment = assets["file"]
        document = {
            "time": int(timezone.now().timestamp() * 1000),
            "version": "2.31.7",
            "blocks": [
                {"type": "header", "data": {"text": "게시글 상세 통합 점검", "level": 1}},
                {"type": "paragraph", "data": {"text": "목차와 <b>모든 주요 블록</b>을 확인하는 공개 게시글입니다."}},
                {"type": "header", "data": {"text": "1. 목차 점검", "level": 2}},
                {"type": "header", "data": {"text": "1.1 목록과 체크리스트", "level": 3}},
                {"type": "list", "data": {"style": "unordered", "items": [{"content": "목록 표시 확인", "meta": {}, "items": []}]}},
                {"type": "list", "data": {"style": "checklist", "items": [{"content": "단계별 확인", "meta": {"checked": True}, "items": []}]}},
                {"type": "quote", "data": {"text": "예상 결과와 실제 결과를 비교합니다.", "caption": "UC-03", "alignment": "left"}},
                {"type": "table", "data": {"withHeadings": True, "content": [["대상", "예상 결과"], ["목차", "H2·H3 표시"], ["첨부", "다운로드 성공"]]}},
                {"type": "warning", "data": {"title": "보안 점검", "message": "위험한 HTML과 URL은 실행되지 않아야 합니다."}},
                {"type": "code", "data": {"code": "const result = '통과';"}},
                {"type": "linkCard", "data": {"url": "https://editorjs.io/", "title": "Editor.js 공식 문서", "description": "블록 데이터 형식 참고"}},
                {"type": "video", "data": {"url": "https://www.youtube.com/watch?v=ysz5S6PUM-U", "caption": "영상 블록"}},
                {"type": "header", "data": {"text": "2. 이미지와 첨부파일", "level": 2}},
                {"type": "image", "data": {"file": {"url": f"/blog/assets/{image.pk}/content/"}, "caption": "UC-03 이미지", "withBorder": True}},
                {"type": "attaches", "data": {"file": {"url": f"/blog/assets/{attachment.pk}/download/", "name": attachment.original_name, "size": attachment.size, "extension": "txt"}, "title": "UC-12 테스트 첨부파일"}},
                {"type": "delimiter", "data": {}},
            ],
        }
        detail_post, _ = Post.objects.update_or_create(
            pk=55003,
            defaults={
                "title": "[UC-03] 게시글 상세·목차·블록·첨부파일 통합 점검",
                "author": users["uc_admin"],
                "category": categories["Development"],
                "content": json.dumps(document, ensure_ascii=False),
                "status": Post.Status.PUBLISHED,
            },
        )
        self._set_tags(detail_post, ("UC-03", "Editor.js", "첨부파일"))

    def _seed_projects(self, users):
        public_project, _ = Project.objects.update_or_create(
            title="[UC-13] 공개 프로젝트",
            defaults={
                "description": "공개 프로젝트와 구성원 권한 점검용입니다.",
                "is_public": True,
                "display_order": 901,
            },
        )
        private_project, _ = Project.objects.update_or_create(
            title="[UC-14] 구성원 전용 비공개 프로젝트",
            defaults={
                "description": "프로젝트 구성원만 관리할 수 있는 연구 공간입니다.",
                "is_public": False,
                "display_order": 902,
            },
        )
        for project in (public_project, private_project):
            ProjectMember.objects.update_or_create(
                project=project,
                user=users["uc_member"],
                defaults={"granted_by": users["uc_admin"]},
            )

        public_post, _ = ProjectPost.objects.update_or_create(
            project=public_project,
            title="[UC-14] 공개 연구 게시글",
            defaults={
                "author": users["uc_member"],
                "content": "공개 프로젝트 상세 조회를 확인합니다.",
                "is_public": True,
            },
        )
        private_post, _ = ProjectPost.objects.update_or_create(
            project=private_project,
            title="[UC-14] 권한 밖에 노출되면 안 되는 연구 게시글",
            defaults={
                "author": users["uc_member"],
                "content": "구성원 권한과 비공개 데이터 노출 방지를 확인합니다.",
                "is_public": False,
            },
        )
        self._set_tags(public_post, ("UC-14", "공개 연구"))
        self._set_tags(private_post, ("UC-14", "비공개 연구"))

    @staticmethod
    def _seed_contacts(admin):
        ContactMessage.objects.update_or_create(
            email="uc-new@example.com",
            message="[UC-04] 새 문의 접수와 알림 발송을 확인합니다.",
            defaults={"name": "새 문의 사용자", "status": ContactMessage.Status.NEW},
        )
        ContactMessage.objects.update_or_create(
            email="uc-progress@example.com",
            message="[UC-15] 관리자 답변 작성과 백그라운드 발송을 확인합니다.",
            defaults={
                "name": "답변 대기 사용자",
                "status": ContactMessage.Status.IN_PROGRESS,
                "reply": "",
                "replied_by": admin,
            },
        )
        ContactMessage.objects.update_or_create(
            email="uc-replied@example.com",
            message="[UC-15] 답변 완료 상태와 발송 시간을 확인합니다.",
            defaults={
                "name": "답변 완료 사용자",
                "status": ContactMessage.Status.REPLIED,
                "reply": "유즈케이스 확인용 답변입니다.",
                "replied_by": admin,
                "replied_at": timezone.now(),
                "email_sent_at": timezone.now(),
            },
        )
