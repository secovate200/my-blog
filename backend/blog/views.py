from pathlib import Path
import hashlib
import json

from django.contrib.auth import (
    authenticate,
    get_user_model,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.urls import reverse
from django.utils.text import slugify
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from .models import BlogAsset, Category, Post, Project, ProjectPost, Tag, UserAccessStatus
from .tasks import enqueue_contact_notifications, enqueue_signup_notification
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
            # 승인되어 로그인한 사용자는 공개 게시글을 읽을 수 있습니다.
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


@require_POST
@csrf_protect
def dashboard_change_password(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "로그인이 필요합니다."}, status=401)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "요청 형식이 올바르지 않습니다."}, status=400)

    current_password = str(data.get("current_password", ""))
    new_password = str(data.get("new_password", ""))
    new_password_confirm = str(data.get("new_password_confirm", ""))
    if not current_password or not new_password or not new_password_confirm:
        return JsonResponse({"detail": "모든 비밀번호 항목을 입력해 주세요."}, status=400)
    if not request.user.check_password(current_password):
        return JsonResponse({"detail": "현재 비밀번호가 올바르지 않습니다."}, status=400)
    if new_password != new_password_confirm:
        return JsonResponse({"detail": "새 비밀번호가 일치하지 않습니다."}, status=400)

    try:
        validate_password(new_password, user=request.user)
    except ValidationError as error:
        return JsonResponse({"detail": " ".join(error.messages)}, status=400)

    request.user.set_password(new_password)
    request.user.save(update_fields=("password",))
    update_session_auth_hash(request, request.user)
    return JsonResponse({"detail": "비밀번호가 변경되었습니다."})


@require_GET
def dashboard_summary(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "로그인이 필요합니다."}, status=401)

    can_view_all_posts = request.user.has_perm("blog.view_post")
    visible_posts = Post.objects.all()
    if not can_view_all_posts:
        visible_posts = visible_posts.filter(status=Post.Status.PUBLISHED)
    visible_categories = Category.objects.all()
    if not can_view_all_posts:
        visible_categories = visible_categories.filter(posts__status=Post.Status.PUBLISHED).distinct()
    managed_projects = Project.objects.all() if request.user.is_superuser else Project.objects.filter(members=request.user)
    can_view_research = request.user.is_superuser or managed_projects.exists()
    recent_posts = visible_posts.select_related("category").order_by("-updated_at")[:5]
    return JsonResponse({
        "counts": {
            "categories": visible_categories.count(),
            "posts": visible_posts.count(),
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
    if request.method == "POST":
        if denied := _require_permission(request, "blog.add_post"):
            return denied
        post, error = _save_dashboard_post(request)
        return error or JsonResponse(_dashboard_post_payload(post), status=201)
    posts = Post.objects.select_related("category").prefetch_related("tags").order_by("-updated_at")
    if not request.user.has_perm("blog.view_post"):
        posts = posts.filter(status=Post.Status.PUBLISHED)
    search = request.GET.get("q", "").strip()
    if search:
        posts = posts.filter(
            Q(title__icontains=search)
            | Q(content__icontains=search)
            | Q(category__name__icontains=search)
            | Q(tags__name__icontains=search)
        ).distinct()
    return JsonResponse({"items": [_dashboard_post_payload(post) for post in posts]})


@require_http_methods(["GET", "PUT", "DELETE"])
@csrf_protect
def dashboard_post_detail(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "로그인이 필요합니다."}, status=401)
    posts = Post.objects.select_related("category").prefetch_related("tags")
    if request.method == "GET" and not request.user.has_perm("blog.view_post"):
        posts = posts.filter(status=Post.Status.PUBLISHED)
    elif request.method != "GET":
        permission = {"PUT": "blog.change_post", "DELETE": "blog.delete_post"}[request.method]
        if denied := _require_permission(request, permission):
            return denied
    post = get_object_or_404(posts, pk=pk)
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
    can_view_all_posts = request.user.has_perm("blog.view_post")
    categories = Category.objects.annotate(
        published_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED)),
        draft_count=Count("posts", filter=Q(posts__status=Post.Status.DRAFT)),
    )
    if not can_view_all_posts:
        categories = categories.filter(published_count__gt=0)
    categories = categories.order_by("name")
    return JsonResponse({"items": [
        {
            "id": category.pk,
            "name": category.name,
            "total": category.published_count + (category.draft_count if can_view_all_posts else 0),
            "published": category.published_count,
            "draft": category.draft_count if can_view_all_posts else 0,
        }
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
    user_model = get_user_model()
    account_user = (
        user_model.objects.filter(email__iexact=account).first()
        if "@" in account
        else user_model.objects.filter(username__iexact=account).first()
    )
    if account_user and account_user.check_password(password):
        access_status, _ = UserAccessStatus.objects.get_or_create(
            user=account_user,
            defaults={"status": UserAccessStatus.Status.APPROVED},
        )
        if access_status.status == UserAccessStatus.Status.PENDING:
            return JsonResponse(
                {"detail": "관리자 승인 대기 중인 계정입니다."}, status=403
            )
        if access_status.status == UserAccessStatus.Status.BANNED:
            detail = "이용이 제한된 계정입니다. 관리자에게 문의해 주세요."
            if access_status.ban_reason:
                detail = f"{detail} 사유: {access_status.ban_reason}"
            return JsonResponse({"detail": detail}, status=403)

    username = account_user.get_username() if account_user else account
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"detail": "아이디 또는 비밀번호를 확인해 주세요."}, status=400)

    login(request, user)
    return JsonResponse(_user_payload(user))


@require_POST
@csrf_protect
def dashboard_signup(request):
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "요청 형식이 올바르지 않습니다."}, status=400)

    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    if not name or not email or not password:
        return JsonResponse({"detail": "모든 항목을 입력해 주세요."}, status=400)
    if len(name) > 150:
        return JsonResponse({"detail": "이름은 150자 이하로 입력해 주세요."}, status=400)

    user_model = get_user_model()
    if user_model.objects.filter(email__iexact=email).exists():
        return JsonResponse({"detail": "이미 사용 중인 이메일입니다."}, status=400)

    local_name = slugify(email.split("@", 1)[0], allow_unicode=True) or "user"
    email_hash = hashlib.sha256(email.encode("utf-8")).hexdigest()[:10]
    username = f"{local_name[:139]}-{email_hash}"
    user = user_model(
        username=username,
        email=email,
        first_name=name,
        is_active=False,
        is_staff=False,
    )
    try:
        user.full_clean(exclude=("password", "last_login", "date_joined"))
        validate_password(password, user=user)
    except ValidationError as error:
        return JsonResponse({"detail": " ".join(error.messages)}, status=400)

    user.set_password(password)
    user.save()
    UserAccessStatus.objects.update_or_create(
        user=user,
        defaults={
            "status": UserAccessStatus.Status.PENDING,
            "ban_reason": "",
            "reviewed_by": None,
            "reviewed_at": None,
        },
    )
    transaction.on_commit(lambda: enqueue_signup_notification(user.pk))
    return JsonResponse(
        {"detail": "회원가입이 완료되었습니다. 관리자 승인 후 로그인할 수 있습니다."},
        status=201,
    )


@require_POST
@csrf_protect
def dashboard_logout(request):
    logout(request)
    return JsonResponse({"logged_out": True})


class BlogAssetUploadAPIView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        can_upload = (
            request.user.is_superuser
            or request.user.has_perm("blog.add_post")
            or Project.objects.filter(members=request.user).exists()
        )
        if not can_upload:
            return Response(
                {"success": 0, "message": "파일을 업로드할 권한이 없습니다."},
                status=403,
            )

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
        # Keep asset URLs on the browser's current origin.  In development the
        # request reaches Django through Vite's proxy, so an absolute URL would
        # otherwise expose an internal host such as ``backend:8000``.
        url = reverse(route, args=[asset.pk])
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
        if not asset.file or not asset.file.storage.exists(asset.file.name):
            raise Http404("첨부파일을 찾을 수 없습니다.")
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
        transaction.on_commit(lambda: enqueue_contact_notifications(contact.pk))
        response_data = {
            **serializer.data,
            "notifications_queued": True,
        }
        return Response(response_data, status=status.HTTP_201_CREATED)
