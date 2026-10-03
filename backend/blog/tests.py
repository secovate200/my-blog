from django.contrib.auth import get_user_model
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Category, ContactMessage, Post, Project, ProjectPost, Tag
from .notifications import send_contact_receipt, send_contact_reply


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
