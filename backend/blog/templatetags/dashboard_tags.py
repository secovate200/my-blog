from django import template

from blog.models import Category, Post, Project, ProjectPost, Tag


register = template.Library()


@register.simple_tag
def dashboard_stats():
    """관리자 홈에 필요한 가벼운 콘텐츠 현황을 한 번에 반환합니다."""

    return {
        "posts": Post.objects.count(),
        "published_posts": Post.objects.filter(status=Post.Status.PUBLISHED).count(),
        "draft_posts": Post.objects.filter(status=Post.Status.DRAFT).count(),
        "projects": Project.objects.count(),
        "public_projects": Project.objects.filter(is_public=True).count(),
        "project_posts": ProjectPost.objects.count(),
        "categories": Category.objects.count(),
        "tags": Tag.objects.count(),
    }
