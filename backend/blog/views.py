from pathlib import Path
import json

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db.models import Count, Prefetch, Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.urls import reverse
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from .models import BlogAsset, Category, Post, Project, ProjectPost, Tag
from .notifications import send_contact_notification, send_contact_receipt
from .serializer import (
    ContactMessageSerializer,
    PostSerializer,
    ProjectDetailSerializer,
    ProjectListSerializer,
    ProjectPostSerializer,
)


class PostPagination(PageNumberPagination):
    page_size = 10


ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
ALLOWED_FILE_EXTENSIONS = {".pdf", ".txt", ".md", ".csv", ".json", ".zip", ".docx", ".xlsx", ".pptx"}


def _user_payload(user):
    has_project_access = user.is_superuser or Project.objects.filter(members=user).exists()
    return {
        "id": user.pk,
        "name": user.get_full_name() or user.get_username(),
        "username": user.get_username(),
        "email": user.email,
        "role": "최고 관리자" if user.is_superuser else "관리자" if user.is_staff else "사용자",
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "permissions": {
            "viewPosts": user.has_perm("blog.view_post"),
            "addPosts": user.has_perm("blog.add_post"),
            "changePosts": user.has_perm("blog.change_post"),
            "deletePosts": user.has_perm("blog.delete_post"),
            "viewCategories": user.has_perm("blog.view_category"),
            "viewProjects": has_project_access,
            "viewResearchPosts": has_project_access,
            "addResearchPosts": has_project_access,
            "changeResearchPosts": has_project_access,
        },
    }


def _require_permission(request, permission):
    if not request.user.has_perm(permission):
        return JsonResponse({"detail": "이 기능을 사용할 권한이 없습니다."}, status=403)
    return None


@require_GET
@ensure_csrf_cookie
def dashboard_csrf(request):
    return JsonResponse({"csrf": "ready"})


@require_GET
def dashboard_current_user(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "로그인이 필요합니다."}, status=401)
    return JsonResponse(_user_payload(request.user))


@require_GET
def dashboard_summary(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "로그인이 필요합니다."}, status=401)

    can_view_posts = request.user.has_perm("blog.view_post")
    can_view_research = request.user.is_superuser or managed_projects.exists()
    recent_posts = Post.objects.select_related("category").order_by("-updated_at")[:5] if can_view_posts else []
    managed_projects = Project.objects.all() if request.user.is_superuser else Project.objects.filter(members=request.user)
    return JsonResponse({
        "counts": {
            "categories": Category.objects.count() if request.user.has_perm("blog.view_category") else 0,
            "posts": Post.objects.count() if can_view_posts else 0,
            "researchPosts": ProjectPost.objects.filter(project__in=managed_projects).count() if can_view_research else 0,
        },
        "recentPosts": [
            {
                "id": post.pk,
                "title": post.title,
                "category": post.category.name,
                "status": "published" if post.status == Post.Status.PUBLISHED else "draft",
                "updatedAt": post.updated_at.isoformat(),
            }
            for post in recent_posts
        ],
    })


def _dashboard_post_payload(post):
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


def _save_dashboard_post(request, post=None):
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return None, JsonResponse({"detail": "요청 형식이 올바르지 않습니다."}, status=400)
    category = get_object_or_404(Category, pk=data.get("category"))
    post = post or Post(author=request.user)
    post.title = str(data.get("title", "")).strip()
    post.category = category
    post.content = data.get("content", "")
    post.status = Post.Status.PUBLISHED if data.get("status") == "published" else Post.Status.DRAFT
    post.save()
    tag_names = [name.strip() for name in str(data.get("tags", "")).split(",") if name.strip()]
    post.tags.set([Tag.objects.get_or_create(name=name)[0] for name in tag_names])
    return post, None


@require_http_methods(["GET", "POST"])
@csrf_protect
def dashboard_posts(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "로그인이 필요합니다."}, status=401)
    permission = "blog.add_post" if request.method == "POST" else "blog.view_post"
    if denied := _require_permission(request, permission):
        return denied
    if request.method == "POST":
        post, error = _save_dashboard_post(request)
        return error or JsonResponse(_dashboard_post_payload(post), status=201)
    posts = Post.objects.select_related("category").prefetch_related("tags").order_by("-updated_at")
    return JsonResponse({"items": [_dashboard_post_payload(post) for post in posts]})


@require_http_methods(["GET", "PUT", "DELETE"])
@csrf_protect
def dashboard_post_detail(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "로그인이 필요합니다."}, status=401)
    permission = {"GET": "blog.view_post", "PUT": "blog.change_post", "DELETE": "blog.delete_post"}[request.method]
    if denied := _require_permission(request, permission):
        return denied
    post = get_object_or_404(Post.objects.select_related("category").prefetch_related("tags"), pk=pk)
    if request.method == "DELETE":
        post.delete()
        return JsonResponse({"deleted": True})
    if request.method == "PUT":
        post, error = _save_dashboard_post(request, post)
        return error or JsonResponse(_dashboard_post_payload(post))
    return JsonResponse(_dashboard_post_payload(post))


@require_GET
def dashboard_categories(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "로그인이 필요합니다."}, status=401)
    if denied := _require_permission(request, "blog.view_category"):
        return denied
    categories = Category.objects.annotate(post_count=Count("posts")).order_by("name")
    return JsonResponse({"items": [
        {"id": category.pk, "name": category.name, "total": category.post_count}
        for category in categories
    ]})


def _managed_projects(user):
    queryset = Project.objects.all() if user.is_superuser else Project.objects.filter(members=user)
    return queryset.distinct()


def _research_post_payload(post):
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


@require_GET
def dashboard_projects(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "로그인이 필요합니다."}, status=401)
    projects = _managed_projects(request.user).annotate(post_count=Count("posts")).order_by("display_order", "-created_at")
    return JsonResponse({"items": [
        {"id": project.pk, "name": project.title, "description": project.description, "postCount": project.post_count}
        for project in projects
    ]})


@require_http_methods(["GET", "POST"])
@csrf_protect
def dashboard_research_posts(request, project_pk):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "로그인이 필요합니다."}, status=401)
    project = get_object_or_404(_managed_projects(request.user), pk=project_pk)
    if request.method == "POST":
        try:
            data = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"detail": "요청 형식이 올바르지 않습니다."}, status=400)
        post = ProjectPost.objects.create(
            project=project,
            author=request.user,
            title=str(data.get("title", "")).strip(),
            content=data.get("content", ""),
            is_public=data.get("visibility") == "public" and data.get("status") == "published",
        )
        tag_names = [name.strip() for name in str(data.get("tags", "")).split(",") if name.strip()]
        post.tags.set([Tag.objects.get_or_create(name=name)[0] for name in tag_names])
        return JsonResponse(_research_post_payload(post), status=201)
    posts = project.posts.select_related("project").prefetch_related("tags").order_by("-updated_at")
    return JsonResponse({"items": [_research_post_payload(post) for post in posts]})


@require_http_methods(["GET", "PUT"])
@csrf_protect
def dashboard_research_post_detail(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "로그인이 필요합니다."}, status=401)
    post = get_object_or_404(
        ProjectPost.objects.select_related("project").prefetch_related("tags").filter(project__in=_managed_projects(request.user)),
        pk=pk,
    )
    if request.method == "PUT":
        try:
            data = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"detail": "요청 형식이 올바르지 않습니다."}, status=400)
        target_project = get_object_or_404(_managed_projects(request.user), pk=data.get("project", post.project_id))
        post.project = target_project
        post.title = str(data.get("title", post.title)).strip()
        post.content = data.get("content", post.content)
        post.is_public = data.get("visibility") == "public" and data.get("status") == "published"
        post.save()
        tag_names = [name.strip() for name in str(data.get("tags", "")).split(",") if name.strip()]
        post.tags.set([Tag.objects.get_or_create(name=name)[0] for name in tag_names])
    return JsonResponse(_research_post_payload(post))


@require_POST
@csrf_protect
def dashboard_login(request):
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "요청 형식이 올바르지 않습니다."}, status=400)

    account = str(data.get("account", "")).strip()
    password = str(data.get("password", ""))
    username = account
    if "@" in account:
        username = (
            get_user_model().objects.filter(email__iexact=account)
            .values_list("username", flat=True)
            .first()
            or account
        )
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"detail": "아이디 또는 비밀번호를 확인해 주세요."}, status=400)
    if not user.is_active:
        return JsonResponse({"detail": "비활성화된 계정입니다."}, status=403)

    login(request, user)
    return JsonResponse(_user_payload(user))


@require_POST
@csrf_protect
def dashboard_logout(request):
    logout(request)
    return JsonResponse({"logged_out": True})


class BlogAssetUploadAPIView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser]

    def post(self, request):
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"success": 0, "message": "파일을 선택해 주세요."}, status=400)

        extension = Path(uploaded.name).suffix.lower()
        is_image = uploaded.content_type in ALLOWED_IMAGE_TYPES and extension in {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        if not is_image and extension not in ALLOWED_FILE_EXTENSIONS:
            return Response({"success": 0, "message": "허용되지 않는 파일 형식입니다."}, status=400)

        limit = 8 * 1024 * 1024 if is_image else 20 * 1024 * 1024
        if uploaded.size > limit:
            return Response({"success": 0, "message": "파일 크기 제한을 초과했습니다."}, status=400)

        asset = BlogAsset.objects.create(
            file=uploaded,
            original_name=Path(uploaded.name).name[:255],
            content_type=uploaded.content_type or "application/octet-stream",
            size=uploaded.size,
            kind=BlogAsset.Kind.IMAGE if is_image else BlogAsset.Kind.FILE,
            uploaded_by=request.user,
        )
        route = "blog:asset-content" if is_image else "blog:asset-download"
        url = request.build_absolute_uri(reverse(route, args=[asset.pk]))
        return Response({
            "success": 1,
            "file": {
                "url": url,
                "name": asset.original_name,
                "size": asset.size,
                "extension": extension.lstrip("."),
            },
        })


class BlogAssetContentAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, pk, download=False):
        try:
            asset = BlogAsset.objects.get(pk=pk)
        except BlogAsset.DoesNotExist as error:
            raise Http404 from error
        response = FileResponse(
            asset.file.open("rb"),
            as_attachment=download or asset.kind == BlogAsset.Kind.FILE,
            filename=asset.original_name,
            content_type=asset.content_type,
        )
        response["X-Content-Type-Options"] = "nosniff"
        return response


class BlogAssetDownloadAPIView(BlogAssetContentAPIView):
    def get(self, request, pk):
        return super().get(request, pk, download=True)


class PostListApiView(ListAPIView):
    """
    공개된 게시글 목록조회 API
    """
    serializer_class = PostSerializer
    pagination_class = PostPagination

    def get_queryset(self):
        # status가 PUBLISHED인 글만 가져옵니다.
        # 초안은 방문자에게 보여주지 않습니다.
        queryset = (
            Post.objects
            .filter(status=Post.Status.PUBLISHED)
            .select_related("category", "author")
            .prefetch_related("tags")
            .order_by("-created_at")
        )

        category = self.request.query_params.get("category")
        tag = self.request.query_params.get("tag")
        search = self.request.query_params.get("q", "").strip()
        if category:
            queryset = queryset.filter(category__name=category)
        if tag:
            queryset = queryset.filter(tags__name=tag)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(content__icontains=search)
                | Q(category__name__icontains=search)
                | Q(tags__name__icontains=search)
            )

        return queryset.distinct()

class PostDetailAPIView(RetrieveAPIView):
    """
    게시글 ID를 이용해 글 하나를 보여주는 API입니다.
    """

    serializer_class = PostSerializer

    def get_queryset(self):
        # 상세 주소에 초안 ID를 넣어도 찾을 수 없게 합니다.
        return (
            Post.objects
            .filter(status=Post.Status.PUBLISHED)
            .select_related("category", "author")
            .prefetch_related("tags")
        )


class ProjectListAPIView(ListAPIView):
    """표시 순서대로 공개 프로젝트만 반환합니다."""

    serializer_class = ProjectListSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            Project.objects.filter(is_public=True)
            .annotate(
                post_count=Count(
                    "posts",
                    filter=Q(posts__is_public=True),
                    distinct=True,
                )
            )
            .order_by("display_order", "-created_at")
        )


class ProjectDetailAPIView(RetrieveAPIView):
    """공개 프로젝트와 그 안의 공개 글만 반환합니다."""

    serializer_class = ProjectDetailSerializer

    def get_queryset(self):
        public_posts = (
            ProjectPost.objects.filter(is_public=True)
            .select_related("author")
            .prefetch_related("tags")
            .order_by("-created_at")
        )
        return (
            Project.objects.filter(is_public=True)
            .annotate(
                post_count=Count(
                    "posts",
                    filter=Q(posts__is_public=True),
                    distinct=True,
                )
            )
            .prefetch_related(Prefetch("posts", queryset=public_posts))
        )


class ProjectPostDetailAPIView(RetrieveAPIView):
    """공개 프로젝트에 속한 공개 프로젝트 글 하나를 반환합니다."""

    serializer_class = ProjectPostSerializer

    def get_queryset(self):
        return (
            ProjectPost.objects.filter(
                project_id=self.kwargs["project_pk"],
                project__is_public=True,
                is_public=True,
            )
            .select_related("project", "author")
            .prefetch_related("tags")
        )


class ContactMessageCreateAPIView(CreateAPIView):
    serializer_class = ContactMessageSerializer
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "contact"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contact = serializer.save()
        notification_sent = send_contact_notification(contact)
        receipt_sent = send_contact_receipt(contact)
        response_data = {
            **serializer.data,
            "notification_sent": notification_sent,
            "receipt_sent": receipt_sent,
        }
        return Response(response_data, status=status.HTTP_201_CREATED)
