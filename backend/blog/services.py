"""블로그 도메인의 저장 규칙과 응답 데이터 가공을 담당하는 서비스 계층입니다.

뷰는 HTTP 요청/응답과 권한 확인에만 집중하고, 여러 엔드포인트에서 재사용되는
게시글 저장·태그 동기화·사용자 권한 계산은 이 모듈에서 일관되게 처리합니다.
"""

import json

from django.db.models import QuerySet

from .content import sanitize_content
from .models import Post, Project, ProjectPost, Tag


class InvalidRequestData(ValueError):
    """JSON 요청 본문을 해석할 수 없을 때 사용하는 도메인 예외입니다."""


def parse_json_body(raw_body: bytes) -> dict:
    """빈 본문은 빈 객체로 처리하고 JSON 객체만 반환합니다."""

    try:
        data = json.loads(raw_body or "{}")
    except json.JSONDecodeError as error:
        raise InvalidRequestData("요청 형식이 올바르지 않습니다.") from error

    # 리스트 같은 JSON도 문법상 유효하지만 이후 .get() 호출을 깨뜨리므로,
    # API 계약에서 요구하는 객체인지 이 경계에서 먼저 검증합니다.
    if not isinstance(data, dict):
        raise InvalidRequestData("요청 형식이 올바르지 않습니다.")
    return data


def get_managed_projects(user) -> QuerySet[Project]:
    """사용자가 관리할 수 있는 프로젝트를 중복 없이 반환합니다."""

    queryset = (
        Project.objects.all()
        if user.is_superuser
        else Project.objects.filter(members=user)
    )
    # through 관계나 추후 권한 조건이 추가되어 JOIN이 늘어도 같은 프로젝트가
    # 두 번 노출되지 않도록 서비스 반환 계약에서 distinct를 보장합니다.
    return queryset.distinct()


def build_user_payload(user) -> dict:
    """프런트엔드 권한 가드가 사용하는 사용자 정보를 구성합니다."""

    has_project_access = user.is_superuser or Project.objects.filter(
        members=user
    ).exists()
    role = "최고 관리자" if user.is_superuser else "관리자" if user.is_staff else "사용자"
    return {
        "id": user.pk,
        "name": user.get_full_name() or user.get_username(),
        "username": user.get_username(),
        "email": user.email,
        "role": role,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "permissions": {
            "viewPosts": True,
            "addPosts": user.has_perm("blog.add_post"),
            "changePosts": user.has_perm("blog.change_post"),
            "deletePosts": user.has_perm("blog.delete_post"),
            "viewCategories": True,
            "viewDraftPosts": user.has_perm("blog.view_post"),
            "viewProjects": has_project_access,
            "viewResearchPosts": has_project_access,
            "addResearchPosts": has_project_access,
            "changeResearchPosts": has_project_access,
        },
    }


def _normalize_tag_names(raw_tags) -> list[str]:
    """쉼표 구분 태그를 정리하고 입력 순서를 유지한 채 중복을 제거합니다."""

    names = (name.strip() for name in str(raw_tags or "").split(","))
    # dict는 삽입 순서를 보존하므로 별도 정렬 없이 사용자가 입력한 순서를
    # 유지하면서 동일 태그를 여러 번 생성하는 실수를 막을 수 있습니다.
    return list(dict.fromkeys(name for name in names if name))


def _sync_tags(instance, raw_tags) -> None:
    """게시글의 태그 집합을 정규화된 입력과 정확히 일치시킵니다."""

    tags = [
        Tag.objects.get_or_create(name=name)[0]
        for name in _normalize_tag_names(raw_tags)
    ]
    instance.tags.set(tags)


def save_dashboard_post(*, user, data: dict, post: Post | None = None) -> Post:
    """일반 게시글을 생성하거나 수정하고 본문과 태그 정책을 적용합니다."""

    target = post or Post(author=user)
    target.title = str(data.get("title", "")).strip()
    target.category_id = data.get("category")
    # 관리자 화면에서 온 본문도 신뢰하지 않습니다. 저장 시점에 정제해야 다른
    # 출력 경로가 추가되더라도 위험한 HTML이 데이터베이스에 남지 않습니다.
    target.content = sanitize_content(data.get("content", ""))
    target.status = (
        Post.Status.PUBLISHED
        if data.get("status") == "published"
        else Post.Status.DRAFT
    )
    target.save()
    _sync_tags(target, data.get("tags"))
    return target


def build_dashboard_post_payload(post: Post) -> dict:
    """관리자 게시글 응답을 프런트엔드 명명 규칙으로 변환합니다."""

    return {
        "id": post.pk,
        "title": post.title,
        "category": post.category.name,
        "categoryId": post.category_id,
        "tags": [tag.name for tag in post.tags.all()],
        "content": post.content,
        "status": "published" if post.status == Post.Status.PUBLISHED else "draft",
        "updatedAt": post.updated_at.isoformat(),
        "createdAt": post.created_at.isoformat(),
    }


def save_research_post(
    *, user, project: Project, data: dict, post: ProjectPost | None = None
) -> ProjectPost:
    """프로젝트 글 생성·수정에 동일한 공개 및 태그 규칙을 적용합니다."""

    target = post or ProjectPost(author=user)
    target.project = project
    target.title = str(data.get("title", target.title if post else "")).strip()
    target.content = data.get("content", target.content if post else "")
    # 공개 범위와 발행 상태가 모두 공개일 때만 외부 API에 노출합니다.
    # 둘 중 하나만 공개인 중간 상태가 실수로 방문자에게 보이는 것을 막습니다.
    target.is_public = (
        data.get("visibility") == "public"
        and data.get("status") == "published"
    )
    target.save()
    _sync_tags(target, data.get("tags"))
    return target


def build_research_post_payload(post: ProjectPost) -> dict:
    """프로젝트 글 응답을 관리자 화면의 데이터 계약으로 변환합니다."""

    return {
        "id": post.pk,
        "projectId": post.project_id,
        "projectName": post.project.title,
        "title": post.title,
        "content": post.content,
        "tags": [tag.name for tag in post.tags.all()],
        "visibility": "public" if post.is_public else "private",
        "status": "published" if post.is_public else "draft",
        "updatedAt": post.updated_at.isoformat(),
        "createdAt": post.created_at.isoformat(),
    }
