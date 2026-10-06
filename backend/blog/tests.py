from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
import tempfile
from unittest.mock import patch

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .content import sanitize_content
from .models import BlogAsset, Category, ContactMessage, Post, Project, ProjectMember, ProjectPost, Tag
from .notifications import send_contact_receipt, send_contact_reply


class RichContentTests(TestCase):
    def test_allowed_notion_blocks_are_preserved(self):
        content = (
            '{"time":1,"version":"2.31.7","blocks":['
            '{"type":"header","data":{"text":"제목","level":2}},'
            '{"type":"paragraph","data":{"text":"<b>본문</b>"}},'
            '{"type":"code","data":{"code":"alert(1)"}}]}'
        )

        sanitized = sanitize_content(content)

        self.assertIn('"type":"header"', sanitized)
        self.assertIn('"text":"<b>본문</b>"', sanitized)
        self.assertIn('"code":"alert(1)"', sanitized)

    def test_all_six_heading_levels_are_preserved(self):
        for level in range(1, 7):
            content = (
                '{"blocks":[{"type":"header","data":'
                f'{{"text":"제목 {level}","level":{level}}}}}]}}'
            )

            self.assertIn(f'"level":{level}', sanitize_content(content))

    def test_quote_trailing_empty_lines_are_removed(self):
        content = (
            '{"blocks":[{"type":"quote","data":'
            '{"text":"너 자신을 알라<br><br><br>","caption":"<br>","alignment":"left"}}]}'
        )

        sanitized = sanitize_content(content)

        self.assertIn('"text":"너 자신을 알라"', sanitized)
        self.assertIn('"caption":""', sanitized)

    def test_unsafe_html_and_link_attributes_are_removed(self):
        content = (
            '{"blocks":[{"type":"paragraph","data":{"text":'
            '"<script>alert(1)</script><a href=\\"javascript:alert(2)\\" '
            'onclick=\\"alert(3)\\">링크</a>"}}]}'
        )

        sanitized = sanitize_content(content)

        self.assertNotIn("onclick", sanitized)
        self.assertNotIn("<script", sanitized)
        self.assertNotIn("javascript:", sanitized)
        self.assertNotIn("onclick", sanitized)
        self.assertIn("alert(1)<a>링크</a>", sanitized)


class BlogAssetTests(TestCase):
    def test_anonymous_user_cannot_upload(self):
        response = self.client.post(
            reverse("blog:asset-upload"),
            {"file": SimpleUploadedFile("test.png", b"image", content_type="image/png")},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(BlogAsset.objects.count(), 0)

    def test_admin_can_upload_and_download_attachment(self):
        user = get_user_model().objects.create_superuser(
            username="asset-admin", email="asset@example.com", password="password"
        )
        self.client.force_login(user)

        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    reverse("blog:asset-upload"),
                    {"file": SimpleUploadedFile("guide.pdf", b"pdf-data", content_type="application/pdf")},
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["success"], 1)
                asset = BlogAsset.objects.get()
                download = self.client.get(reverse("blog:asset-download", args=[asset.pk]))
                self.assertEqual(download.status_code, 200)
                self.assertIn("attachment", download["Content-Disposition"])


class DashboardAuthenticationTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="dashboard-admin",
            email="dashboard@example.com",
            password="secure-password",
        )
        self.regular_user = get_user_model().objects.create_user(
            username="regular-user",
            password="secure-password",
        )

    def test_csrf_endpoint_sets_cookie(self):
        response = self.client.get(reverse("blog:dashboard-csrf"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)

    def test_staff_user_can_login_with_username_and_read_session(self):
        response = self.client.post(
            reverse("blog:dashboard-login"),
            data={"account": "dashboard-admin", "password": "secure-password"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "dashboard-admin")
        current = self.client.get(reverse("blog:dashboard-current-user"))
        self.assertEqual(current.status_code, 200)
        self.assertTrue(current.json()["is_superuser"])

    def test_staff_user_can_login_with_email(self):
        response = self.client.post(
            reverse("blog:dashboard-login"),
            data={"account": "dashboard@example.com", "password": "secure-password"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

    def test_regular_user_can_login_to_dashboard_without_admin_access(self):
        response = self.client.post(
            reverse("blog:dashboard-login"),
            data={"account": "regular-user", "password": "secure-password"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["is_staff"])
        self.assertEqual(response.json()["role"], "사용자")

    def test_dashboard_summary_uses_database_counts_and_recent_posts(self):
        category = Category.objects.create(name="Database")
        Post.objects.create(
            title="DB 게시글",
            author=self.admin,
            category=category,
            content="{}",
            status=Post.Status.PUBLISHED,
        )
        project = Project.objects.create(title="연구", description="테스트")
        ProjectMember.objects.create(project=project, user=self.regular_user, granted_by=self.admin)
        ProjectPost.objects.create(
            project=project,
            author=self.admin,
            title="연구 글",
            content="{}",
        )
        self.regular_user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="blog",
            codename__in=["view_category", "view_post", "view_project", "view_projectpost"],
        ))
        self.client.force_login(self.regular_user)

        response = self.client.get(reverse("blog:dashboard-summary"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["counts"], {
            "categories": 1,
            "posts": 1,
            "researchPosts": 1,
        })
        self.assertEqual(response.json()["recentPosts"][0]["title"], "DB 게시글")
        projects = self.client.get(reverse("blog:dashboard-projects"))
        self.assertEqual([item["name"] for item in projects.json()["items"]], ["연구"])

    def test_user_without_group_permission_cannot_read_posts(self):
        self.client.force_login(self.regular_user)

        response = self.client.get(reverse("blog:dashboard-posts"))

        self.assertEqual(response.status_code, 403)

    @override_settings(DASHBOARD_LOGIN_URL="http://localhost:5174/#/login")
    def test_admin_logout_ends_session_and_redirects_to_dashboard_login(self):
        self.client.force_login(self.admin)

        response = self.client.post(reverse("dashboard-admin-logout"))

        self.assertRedirects(
            response,
            "http://localhost:5174/#/login",
            fetch_redirect_response=False,
        )
        self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(DASHBOARD_LOGIN_URL="http://localhost:5174/#/login")
    def test_admin_login_redirects_to_dashboard_login(self):
        response = self.client.get(reverse("dashboard-admin-login"))

        self.assertRedirects(
            response,
            "http://localhost:5174/#/login",
            fetch_redirect_response=False,
        )

    @override_settings(DASHBOARD_FORBIDDEN_URL="http://localhost:5174/#/403")
    def test_non_staff_admin_access_redirects_to_dashboard_forbidden_page(self):
        self.client.force_login(self.regular_user)

        admin_response = self.client.get(reverse("admin:index"))
        self.assertEqual(admin_response.status_code, 302)

        response = self.client.get(admin_response["Location"])

        self.assertRedirects(
            response,
            "http://localhost:5174/#/403",
            fetch_redirect_response=False,
        )

    def test_logout_clears_dashboard_session(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("blog:dashboard-logout"))

        self.assertEqual(response.status_code, 200)
        current = self.client.get(reverse("blog:dashboard-current-user"))
        self.assertEqual(current.status_code, 401)


class PostPaginationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        author = get_user_model().objects.create_user(username="author")
        category = Category.objects.create(name="Pagination Test")
        Post.objects.bulk_create(
            [
                Post(
                    title=str(number),
                    author=author,
                    category=category,
                    content=f"{number}번 게시글",
                    status=Post.Status.PUBLISHED,
                )
                for number in range(1, 21)
            ]
        )

    def test_post_list_is_paginated_by_ten(self):
        first_page = self.client.get(reverse("blog:post-list"))
        second_page = self.client.get(reverse("blog:post-list"), {"page": 2})

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(first_page.json()["count"], 20)
        self.assertEqual(len(first_page.json()["results"]), 10)
        self.assertIsNotNone(first_page.json()["next"])
        self.assertEqual(len(second_page.json()["results"]), 10)
        self.assertIsNone(second_page.json()["next"])

    def test_post_list_can_be_filtered_before_pagination(self):
        other_category = Category.objects.create(name="Other")
        Post.objects.create(
            title="other",
            author=get_user_model().objects.get(username="author"),
            category=other_category,
            content="다른 카테고리 게시글",
            status=Post.Status.PUBLISHED,
        )

        response = self.client.get(
            reverse("blog:post-list"),
            {"category": "Pagination Test"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 20)
        self.assertTrue(
            all(
                post["category"] == "Pagination Test"
                for post in response.json()["results"]
            )
        )

    def test_draft_post_is_hidden_from_public_list_and_detail(self):
        draft = Post.objects.create(
            title="Private Draft",
            author=get_user_model().objects.get(username="author"),
            category=Category.objects.get(name="Pagination Test"),
            content="외부에 공개하면 안 되는 내용",
            status=Post.Status.DRAFT,
        )

        list_response = self.client.get(reverse("blog:post-list"), {"q": "Private Draft"})
        detail_response = self.client.get(reverse("blog:post-detail", args=[draft.pk]))

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["count"], 0)
        self.assertEqual(detail_response.status_code, 404)

    def test_post_list_can_search_title_content_category_and_tag(self):
        tag = Tag.objects.create(name="SearchableTag")
        searchable_post = Post.objects.create(
            title="Unique Security Title",
            author=get_user_model().objects.get(username="author"),
            category=Category.objects.get(name="Pagination Test"),
            content="검색 가능한 특별한 본문",
            status=Post.Status.PUBLISHED,
        )
        searchable_post.tags.add(tag)

        for query in [
            "Unique Security",
            "특별한 본문",
            "Pagination Test",
            "SearchableTag",
        ]:
            with self.subTest(query=query):
                response = self.client.get(
                    reverse("blog:post-list"),
                    {"q": query},
                )
                self.assertEqual(response.status_code, 200)
                self.assertGreater(response.json()["count"], 0)

        tag_response = self.client.get(
            reverse("blog:post-list"),
            {"q": "SearchableTag"},
        )
        self.assertEqual(tag_response.json()["count"], 1)
        self.assertEqual(tag_response.json()["results"][0]["id"], searchable_post.pk)


class ProjectApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        author = get_user_model().objects.create_user(username="project-author")
        tag = Tag.objects.create(name="React")
        cls.public_project = Project.objects.create(
            title="Public Project",
            description="공개 프로젝트",
            is_public=True,
            display_order=1,
        )
        cls.private_project = Project.objects.create(
            title="Private Project",
            description="비공개 프로젝트",
            is_public=False,
            display_order=0,
        )
        cls.public_post = ProjectPost.objects.create(
            project=cls.public_project,
            author=author,
            title="Public Log",
            content="공개 프로젝트 글",
            is_public=True,
        )
        cls.public_post.tags.add(tag)
        ProjectPost.objects.create(
            project=cls.public_project,
            author=author,
            title="Private Log",
            content="비공개 프로젝트 글",
            is_public=False,
        )

    def test_project_list_only_contains_public_projects(self):
        response = self.client.get(reverse("blog:project-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["title"], "Public Project")
        self.assertEqual(response.json()[0]["post_count"], 1)
        self.assertEqual(response.json()[0]["tags"], ["React"])

    def test_project_detail_only_contains_public_posts(self):
        response = self.client.get(
            reverse("blog:project-detail", args=[self.public_project.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["posts"]), 1)
        self.assertEqual(response.json()["posts"][0]["title"], "Public Log")

    def test_private_project_detail_is_not_accessible(self):
        response = self.client.get(
            reverse("blog:project-detail", args=[self.private_project.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_public_project_post_detail_is_accessible(self):
        response = self.client.get(
            reverse(
                "blog:project-post-detail",
                args=[self.public_project.pk, self.public_post.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Public Log")
        self.assertEqual(response.json()["project"], self.public_project.pk)
        self.assertEqual(response.json()["project_title"], "Public Project")

    def test_project_post_cannot_be_read_through_another_project(self):
        other_project = Project.objects.create(
            title="Other Public Project",
            description="다른 공개 프로젝트",
            is_public=True,
        )

        response = self.client.get(
            reverse(
                "blog:project-post-detail",
                args=[other_project.pk, self.public_post.pk],
            )
        )

        self.assertEqual(response.status_code, 404)


class ContactMessageTests(TestCase):
    @patch("blog.views.send_contact_notification", return_value=True)
    @patch("blog.views.send_contact_receipt", return_value=True)
    def test_contact_message_is_saved_and_notified(self, receipt, notify):
        response = self.client.post(
            reverse("blog:contact-create"),
            {
                "name": "방문자",
                "email": "visitor@example.com",
                "message": "블로그 문의입니다.",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["notification_sent"])
        self.assertTrue(response.json()["receipt_sent"])
        self.assertEqual(ContactMessage.objects.count(), 1)
        notify.assert_called_once_with(ContactMessage.objects.get())
        receipt.assert_called_once_with(ContactMessage.objects.get())

    @patch("blog.views.send_contact_notification", return_value=True)
    @patch("blog.views.send_contact_receipt", return_value=True)
    def test_logged_in_admin_can_submit_without_csrf_token(self, receipt, notify):
        user = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)

        response = client.post(
            reverse("blog:contact-create"),
            {
                "name": "관리자",
                "email": "admin@example.com",
                "message": "로그인 상태에서 보낸 문의입니다.",
            },
        )

        self.assertEqual(response.status_code, 201)
        notify.assert_called_once_with(ContactMessage.objects.get())
        receipt.assert_called_once_with(ContactMessage.objects.get())

    @patch("blog.views.send_contact_notification")
    @patch("blog.views.send_contact_receipt")
    def test_invalid_contact_message_is_rejected(self, receipt, notify):
        response = self.client.post(
            reverse("blog:contact-create"),
            {"name": "", "email": "invalid", "message": ""},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(ContactMessage.objects.count(), 0)
        notify.assert_not_called()
        receipt.assert_not_called()

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        EMAIL_HOST="smtp.example.com",
        DEFAULT_FROM_EMAIL="SECOVATE200 BLOG <blog@example.com>",
    )
    def test_receipt_email_contains_inline_logo(self):
        contact = ContactMessage.objects.create(
            name="방문자",
            email="visitor@example.com",
            message="문의 내용",
        )

        self.assertTrue(send_contact_receipt(contact))
        contact.refresh_from_db()

        self.assertIsNotNone(contact.receipt_sent_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["visitor@example.com"])
        self.assertIn("문의가 정상 접수되었습니다", mail.outbox[0].alternatives[0].content)
        self.assertTrue(
            any(
                attachment.get("Content-ID") == "<secovate200-logo>"
                for attachment in mail.outbox[0].attachments
            )
        )

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        EMAIL_HOST="smtp.example.com",
        DEFAULT_FROM_EMAIL="SECOVATE200 BLOG <blog@example.com>",
    )
    def test_reply_email_is_sent_to_contact_address(self):
        contact = ContactMessage.objects.create(
            name="<방문자>",
            email="visitor@example.com",
            message="원래 문의 첫 줄\n<문의 두 번째 줄>",
            reply="첫 번째 줄\n두 번째 줄",
        )

        self.assertTrue(send_contact_reply(contact))

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["visitor@example.com"])
        html = mail.outbox[0].alternatives[0].content
        self.assertIn("원래 문의 첫 줄<br>&lt;문의 두 번째 줄&gt;", html)
        self.assertIn("첫 번째 줄<br>두 번째 줄", html)
        self.assertIn("&lt;방문자&gt;", html)


class FrameProtectionTests(TestCase):
    def test_responses_only_allow_same_origin_frames(self):
        response = self.client.get(reverse("blog:post-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Frame-Options"], "SAMEORIGIN")
        self.assertEqual(
            response.headers["Content-Security-Policy"],
            "frame-ancestors 'self'",
        )
