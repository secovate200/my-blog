"""SmartBase dashboard widgets for day-to-day blog administration."""

from django import forms
from django.urls import reverse
from django_smartbase_admin.engine.dashboard import SBAdminDashboardHtmlWidget

from blog.models import ContactMessage, Post, Project, ProjectPost, UserAccessStatus


class MyBlogOverviewWidget(SBAdminDashboardHtmlWidget):
    widget_id = "my_blog_overview"
    name = "운영 현황"
    template_name = "sb_admin/dashboard/my_blog_overview_widget.html"
    content_template_name = "sb_admin/dashboard/my_blog_overview.html"
    media = forms.Media(css={"all": ("admin/smartbase-dashboard.css",)})

    def get_html_context_data(self, request):
        user = request.user
        is_superuser = user.is_superuser

        projects = Project.objects.all()
        project_posts = ProjectPost.objects.select_related("project", "author")
        if not is_superuser:
            projects = projects.filter(members=user).distinct()
            project_posts = project_posts.filter(project__members=user).distinct()

        stats = [
            {
                "label": "관리 프로젝트",
                "value": projects.count(),
                "url": reverse("sb_admin:blog_project_changelist"),
                "tone": "blue",
            },
        ]
        if is_superuser:
            stats[0:0] = [
                {
                    "label": "전체 게시글",
                    "value": Post.objects.count(),
                    "url": reverse("sb_admin:blog_post_changelist"),
                    "tone": "teal",
                },
                {
                    "label": "공개 게시글",
                    "value": Post.objects.filter(status=Post.Status.PUBLISHED).count(),
                    "url": reverse("sb_admin:blog_post_changelist"),
                    "tone": "green",
                },
            ]
            stats.append(
                {
                    "label": "승인 요청 대기",
                    "value": UserAccessStatus.objects.filter(
                        status=UserAccessStatus.Status.PENDING
                    ).count(),
                    "url": reverse("sb_admin:auth_user_changelist"),
                    "tone": "violet",
                }
            )
            stats.append(
                {
                    "label": "미답변 문의",
                    "value": ContactMessage.objects.exclude(
                        status=ContactMessage.Status.REPLIED
                    ).count(),
                    "url": reverse("sb_admin:blog_contactmessage_changelist"),
                    "tone": "amber",
                }
            )

        quick_actions = [
            {
                "label": "프로젝트 관리",
                "description": "공개 여부와 표시 순서를 조정합니다.",
                "url": reverse("sb_admin:blog_project_changelist"),
                "icon": "project",
            },
        ]
        if is_superuser:
            quick_actions[0:0] = [
                {
                    "label": "새 게시글 작성",
                    "description": "블로그에 게시할 글을 작성합니다.",
                    "url": reverse("sb_admin:blog_post_add"),
                    "icon": "write",
                },
                {
                    "label": "문의 확인",
                    "description": "새로 접수된 문의를 확인하고 답변합니다.",
                    "url": reverse("sb_admin:blog_contactmessage_changelist"),
                    "icon": "mail",
                },
                {
                    "label": "가입 승인 요청",
                    "description": "승인 대기 중인 사용자를 확인합니다.",
                    "url": reverse("sb_admin:auth_user_changelist"),
                    "icon": "user",
                },
            ]
        else:
            quick_actions.insert(
                0,
                {
                    "label": "프로젝트 글 작성",
                    "description": "프로젝트에 새 콘텐츠를 추가합니다.",
                    "url": reverse("sb_admin:blog_projectpost_add"),
                    "icon": "write",
                },
            )

        recent_posts = project_posts.order_by("-created_at")[:5]
        if is_superuser:
            recent_posts = Post.objects.select_related("category", "author").order_by(
                "-created_at"
            )[:5]

        return {
            "stats": stats,
            "quick_actions": quick_actions,
            "recent_posts": recent_posts,
            "recent_title": "최근 블로그 글" if is_superuser else "최근 프로젝트 글",
            "is_superuser": is_superuser,
            "display_name": user.get_full_name() or user.get_username(),
        }
