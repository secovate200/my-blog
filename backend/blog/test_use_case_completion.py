"""배포 전 유즈케이스에서 비어 있던 정상·권한·예외 흐름을 검증합니다.

외부 SMTP와 Discord에는 실제 데이터를 보내지 않고 성공·실패 응답을 재현합니다.
이 방식은 테스트를 반복해도 제3자에게 중복 알림을 보내지 않으면서, DB 상태와
백그라운드 작업의 복구 규칙을 결정적으로 확인하기 위해 필요합니다.
"""

import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import (
    BlogAsset,
    Category,
    ContactMessage,
    Post,
    Project,
    ProjectMember,
    ProjectPost,
    UserAccessStatus,
)
from .notifications import send_account_approval_email
from .tasks import _run_contact_reply


class SignupAndApprovalCompletionTests(TestCase):
    """UC-05와 UC-08의 중복·정책·중복 알림 방지 흐름을 확인합니다."""

    def test_duplicate_email_and_weak_password_are_rejected(self):
        get_user_model().objects.create_user(
            username="existing",
            email="existing@example.com",
            password="Strong-password-123!",
        )

        duplicate = self.client.post(
            reverse("blog:dashboard-signup"),
            {"name": "중복", "email": "EXISTING@example.com", "password": "Strong-password-123!"},
            content_type="application/json",
        )
        weak = self.client.post(
            reverse("blog:dashboard-signup"),
            {"name": "취약", "email": "weak@example.com", "password": "1234"},
            content_type="application/json",
        )

        self.assertEqual(duplicate.status_code, 400)
        self.assertIn("이미 사용 중", duplicate.json()["detail"])
        self.assertEqual(weak.status_code, 400)
        self.assertFalse(get_user_model().objects.filter(email="weak@example.com").exists())

    def test_pending_and_banned_users_receive_korean_status_messages(self):
        pending = get_user_model().objects.create_user(
            username="pending", email="pending@example.com", password="Strong-password-123!", is_active=True
        )
        pending.access_status.status = UserAccessStatus.Status.PENDING
        pending.access_status.save()
        banned = get_user_model().objects.create_user(
            username="banned", email="banned@example.com", password="Strong-password-123!", is_active=True
        )
        banned.access_status.status = UserAccessStatus.Status.BANNED
        banned.access_status.ban_reason = "테스트 차단"
        banned.access_status.save()

        pending_response = self.client.post(
            reverse("blog:dashboard-login"),
            {"email": "pending@example.com", "password": "Strong-password-123!"},
            content_type="application/json",
        )
        banned_response = self.client.post(
            reverse("blog:dashboard-login"),
            {"email": "banned@example.com", "password": "Strong-password-123!"},
            content_type="application/json",
        )

        self.assertEqual(pending_response.status_code, 403)
        self.assertIn("승인 대기", pending_response.json()["detail"])
        self.assertEqual(banned_response.status_code, 403)
        self.assertIn("테스트 차단", banned_response.json()["detail"])

    @patch("blog.signals.enqueue_account_approval_email")
    def test_approval_notification_is_not_queued_twice(self, enqueue):
        user = get_user_model().objects.create_user(username="approval-target")
        access = user.access_status
        access.status = UserAccessStatus.Status.PENDING
        access.save()

        with self.captureOnCommitCallbacks(execute=True):
            access.status = UserAccessStatus.Status.APPROVED
            access.save()
        with self.captureOnCommitCallbacks(execute=True):
            access.save()

        enqueue.assert_called_once_with(user.pk)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        EMAIL_HOST="smtp.example.com",
        DEFAULT_FROM_EMAIL="SECOVATE200 BLOG <blog@example.com>",
        DASHBOARD_LOGIN_URL="http://localhost:5175/#/login",
    )
    def test_approval_email_is_built_and_sent_without_external_smtp(self):
        user = get_user_model().objects.create_user(
            username="mail-target", email="target@example.com", first_name="승인 대상"
        )

        self.assertTrue(send_account_approval_email(user))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["target@example.com"])
        self.assertIn("계정 승인이 완료", mail.outbox[0].subject)

    @override_settings(
        EMAIL_HOST="smtp.example.com",
        DEFAULT_FROM_EMAIL="SECOVATE200 BLOG <blog@example.com>",
    )
    @patch("blog.notifications.EmailMultiAlternatives.send", side_effect=OSError("SMTP 중단"))
    def test_approval_email_failure_returns_false_without_reverting_approval(self, _send):
        user = get_user_model().objects.create_user(
            username="mail-failure", email="failure@example.com"
        )
        user.access_status.status = UserAccessStatus.Status.APPROVED
        user.access_status.save()

        with self.assertLogs("blog.notifications", level="ERROR") as logs:
            result = send_account_approval_email(user)

        user.access_status.refresh_from_db()
        self.assertFalse(result)
        self.assertEqual(user.access_status.status, UserAccessStatus.Status.APPROVED)
        self.assertTrue(any("발송에 실패" in message for message in logs.output))


class PostCrudCompletionTests(TestCase):
    """UC-10과 UC-11의 생성·임시 저장·공개·수정·삭제를 한 흐름으로 검증합니다."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="editor")
        self.user.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="blog",
                codename__in=["add_post", "change_post", "delete_post", "view_post"],
            )
        )
        self.category = Category.objects.create(name="통합 테스트")
        self.client.force_login(self.user)

    def _payload(self, *, title="작성 테스트", status="draft"):
        return {
            "title": title,
            "category": self.category.pk,
            "tags": "작성, Editor.js, 작성",
            "status": status,
            "content": json.dumps({"blocks": [{"type": "paragraph", "data": {"text": "본문"}}]}),
        }

    def test_editor_can_create_publish_update_and_delete_post(self):
        created = self.client.post(
            reverse("blog:dashboard-posts"), self._payload(), content_type="application/json"
        )
        self.assertEqual(created.status_code, 201)
        post_id = created.json()["id"]
        self.assertEqual(created.json()["status"], "draft")
        # 다대다 조회의 DB 정렬 순서는 계약이 아니므로 태그 집합과 중복 제거만 확인합니다.
        self.assertCountEqual(created.json()["tags"], ["작성", "Editor.js"])
        self.assertEqual(
            self.client.get(reverse("blog:post-detail", args=[post_id])).status_code,
            404,
        )

        updated = self.client.put(
            reverse("blog:dashboard-post-detail", args=[post_id]),
            self._payload(title="수정된 공개 글", status="published"),
            content_type="application/json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["title"], "수정된 공개 글")
        self.assertEqual(
            self.client.get(reverse("blog:post-detail", args=[post_id])).status_code,
            200,
        )

        deleted = self.client.delete(reverse("blog:dashboard-post-detail", args=[post_id]))
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(Post.objects.filter(pk=post_id).exists())

    def test_missing_category_and_invalid_json_are_rejected_without_creating_post(self):
        missing_category = self.client.post(
            reverse("blog:dashboard-posts"),
            {**self._payload(), "category": 999999},
            content_type="application/json",
        )
        invalid_json = self.client.post(
            reverse("blog:dashboard-posts"), "{invalid", content_type="application/json"
        )

        self.assertEqual(missing_category.status_code, 404)
        self.assertEqual(invalid_json.status_code, 400)
        self.assertEqual(Post.objects.count(), 0)


class AssetValidationCompletionTests(TestCase):
    """UC-12의 확장자·MIME·용량 제한과 정상 XLSX 업로드를 검증합니다."""

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(username="asset-completion")
        self.client.force_login(self.user)
        self.temp_root = Path(settings.BASE_DIR) / ".test-temp"
        self.temp_root.mkdir(parents=True, exist_ok=True)

    def test_rejects_disallowed_extension_mime_mismatch_and_oversized_image(self):
        with tempfile.TemporaryDirectory(dir=self.temp_root) as media_root:
            with self.settings(MEDIA_ROOT=media_root):
                executable = self.client.post(
                    reverse("blog:asset-upload"),
                    {"file": SimpleUploadedFile("danger.exe", b"MZ", content_type="application/x-msdownload")},
                )
                disguised = self.client.post(
                    reverse("blog:asset-upload"),
                    {"file": SimpleUploadedFile("fake.xlsx", b"MZ", content_type="application/x-msdownload")},
                )
                oversized = self.client.post(
                    reverse("blog:asset-upload"),
                    {"file": SimpleUploadedFile("large.png", b"x" * (8 * 1024 * 1024 + 1), content_type="image/png")},
                )

        self.assertEqual(executable.status_code, 400)
        self.assertEqual(disguised.status_code, 400)
        self.assertIn("MIME", disguised.json()["message"])
        self.assertEqual(oversized.status_code, 400)
        self.assertEqual(BlogAsset.objects.count(), 0)

    def test_valid_xlsx_returns_relative_download_url(self):
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        with tempfile.TemporaryDirectory(dir=self.temp_root) as media_root:
            with self.settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    reverse("blog:asset-upload"),
                    {"file": SimpleUploadedFile("report.xlsx", b"xlsx", content_type=mime)},
                )
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json()["file"]["url"].startswith("/blog/assets/"))
                self.assertNotIn("backend:", response.json()["file"]["url"])


class ProjectAndResearchCompletionTests(TestCase):
    """UC-13과 UC-14의 구성원 변경 및 연구 글 생명주기를 검증합니다."""

    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(username="project-admin")
        self.member = get_user_model().objects.create_user(username="project-member")
        self.outsider = get_user_model().objects.create_user(username="project-outsider")
        self.project = Project.objects.create(title="비공개 연구", is_public=False)
        ProjectMember.objects.create(
            project=self.project, user=self.member, granted_by=self.admin
        )

    def test_membership_removal_immediately_revokes_dashboard_access(self):
        self.client.force_login(self.member)
        allowed = self.client.get(reverse("blog:dashboard-projects"))
        self.assertEqual([item["id"] for item in allowed.json()["items"]], [self.project.pk])

        ProjectMember.objects.filter(project=self.project, user=self.member).delete()
        revoked = self.client.get(reverse("blog:dashboard-projects"))
        self.assertEqual(revoked.json()["items"], [])

    def test_member_can_create_update_and_publish_research_but_outsider_cannot_read_it(self):
        self.client.force_login(self.member)
        created = self.client.post(
            reverse("blog:dashboard-research-posts", args=[self.project.pk]),
            {
                "project": self.project.pk,
                "title": "연구 통합 테스트",
                "content": "초안 본문",
                "tags": "연구, 보안",
                "visibility": "private",
                "status": "draft",
            },
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 201)
        post_id = created.json()["id"]
        self.assertFalse(ProjectPost.objects.get(pk=post_id).is_public)

        updated = self.client.put(
            reverse("blog:dashboard-research-post-detail", args=[post_id]),
            {
                "project": self.project.pk,
                "title": "공개 연구 보고서",
                "content": "수정된 본문",
                "tags": "연구",
                "visibility": "public",
                "status": "published",
            },
            content_type="application/json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertTrue(ProjectPost.objects.get(pk=post_id).is_public)

        self.client.force_login(self.outsider)
        denied = self.client.get(reverse("blog:dashboard-research-post-detail", args=[post_id]))
        self.assertEqual(denied.status_code, 404)


class NotificationFailureCompletionTests(TestCase):
    """UC-04·08·15에서 외부 실패가 핵심 DB 상태를 훼손하지 않는지 확인합니다."""

    @patch("blog.tasks.send_contact_reply", return_value=False)
    def test_failed_reply_keeps_contact_retryable(self, send_reply):
        admin = get_user_model().objects.create_superuser(username="reply-failure-admin")
        contact = ContactMessage.objects.create(
            name="문의자",
            email="visitor@example.com",
            message="문의",
            reply="답변",
            status=ContactMessage.Status.IN_PROGRESS,
        )

        with self.assertLogs("blog.tasks", level="WARNING") as logs:
            _run_contact_reply(contact.pk, admin.pk)

        contact.refresh_from_db()
        self.assertEqual(contact.status, ContactMessage.Status.IN_PROGRESS)
        self.assertIsNone(contact.email_sent_at)
        self.assertTrue(any("발송에 실패" in message for message in logs.output))
        send_reply.assert_called_once_with(contact)

