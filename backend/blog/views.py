"""HTTP 요청을 검증하고 서비스 계층의 결과를 응답으로 변환하는 API 뷰입니다.

저장 규칙은 services.py에 위임해 재사용하고, 이 파일은 인증·권한·상태 코드처럼
HTTP 경계에서만 필요한 책임을 맡습니다.
"""

import hashlib
import mimetypes
from pathlib import Path

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
from .models import BlogAsset, Category, Post, Project, ProjectPost, SiteProfile, UserAccessStatus
from .services import (
    InvalidRequestData,
    build_dashboard_post_payload,
    build_research_post_payload,
    build_user_payload,
    get_managed_projects,
    parse_json_body,
    save_dashboard_post,
    save_research_post,
)
from .tasks import enqueue_contact_notifications, enqueue_signup_notification
from .serializer import (
    ContactMessageReadSerializer,
    ContactMessageWriteSerializer,
    PostSerializer,
    ProjectDetailSerializer,
    ProjectListSerializer,
    ProjectPostSerializer,
    SiteProfileReadSerializer,
)


class SiteProfileAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        profile, _ = SiteProfile.objects.get_or_create(
            pk=1,
            defaults={
                "name": "SECOVATE200",
                "role": "BUG HUNTER",
                "bio": "보안 취약점과 개발 과정에서 배운 내용을 기록합니다.",
            },
        )
        return Response(SiteProfileReadSerializer(profile).data)


@require_GET
def site_profile_logo(request):
    profile = get_object_or_404(SiteProfile, pk=1)
    if not profile.logo:
        raise Http404
    content_type = mimetypes.guess_type(profile.logo.name)[0] or "application/octet-stream"
    return FileResponse(profile.logo.open("rb"), content_type=content_type)


class PostPagination(PageNumberPagination):
    page_size = 10


ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
ALLOWED_FILE_TYPES = {
    ".pdf": {"application/pdf"},
    ".txt": {"text/plain"},
    ".md": {"text/markdown", "text/plain"},
    ".csv": {"text/csv", "application/csv"},
    ".json": {"application/json"},
    ".zip": {"application/zip", "application/x-zip-compressed"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    ".pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation"},
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
    return JsonResponse(build_user_payload(request.user))


@require_POST
@csrf_protect
def dashboard_change_password(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "로그인이 필요합니다."}, status=401)

    try:
        data = parse_json_body(request.body)
    except InvalidRequestData as error:
        return JsonResponse({"detail": str(error)}, status=400)

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


def _save_dashboard_post(request, post=None):
    try:
        data = parse_json_body(request.body)
        # 존재하지 않는 category_id는 모델 저장 단계의 무결성 오류가 되기 전에
        # 일관된 404 응답으로 변환하기 위해 서비스 호출 전 확인합니다.
        get_object_or_404(Category, pk=data.get("category"))
        return save_dashboard_post(user=request.user, data=data, post=post), None
    except InvalidRequestData as error:
        return None, JsonResponse({"detail": str(error)}, status=400)


@require_http_methods(["GET", "POST"])
@csrf_protect
def dashboard_posts(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "로그인이 필요합니다."}, status=401)
    if request.method == "POST":
        if denied := _require_permission(request, "blog.add_post"):
            return denied
        post, error = _save_dashboard_post(request)
        return error or JsonResponse(build_dashboard_post_payload(post), status=201)
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
    return JsonResponse({"items": [build_dashboard_post_payload(post) for post in posts]})


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
        return error or JsonResponse(build_dashboard_post_payload(post))
    return JsonResponse(build_dashboard_post_payload(post))


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


@require_GET
def dashboard_projects(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "로그인이 필요합니다."}, status=401)
    projects = get_managed_projects(request.user).annotate(post_count=Count("posts")).order_by("display_order", "-created_at")
    return JsonResponse({"items": [
        {"id": project.pk, "name": project.title, "description": project.description, "postCount": project.post_count}
        for project in projects
    ]})


@require_http_methods(["GET", "POST"])
@csrf_protect
def dashboard_research_posts(request, project_pk):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "로그인이 필요합니다."}, status=401)
    project = get_object_or_404(get_managed_projects(request.user), pk=project_pk)
    if request.method == "POST":
        try:
            data = parse_json_body(request.body)
        except InvalidRequestData as error:
            return JsonResponse({"detail": str(error)}, status=400)
        post = save_research_post(user=request.user, project=project, data=data)
        return JsonResponse(build_research_post_payload(post), status=201)
    posts = project.posts.select_related("project").prefetch_related("tags").order_by("-updated_at")
    return JsonResponse({"items": [build_research_post_payload(post) for post in posts]})


@require_http_methods(["GET", "PUT"])
@csrf_protect
def dashboard_research_post_detail(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "로그인이 필요합니다."}, status=401)
    post = get_object_or_404(
        ProjectPost.objects.select_related("project").prefetch_related("tags").filter(project__in=get_managed_projects(request.user)),
        pk=pk,
    )
    if request.method == "PUT":
        try:
            data = parse_json_body(request.body)
        except InvalidRequestData as error:
            return JsonResponse({"detail": str(error)}, status=400)
        target_project = get_object_or_404(get_managed_projects(request.user), pk=data.get("project", post.project_id))
        post = save_research_post(user=request.user, project=target_project, data=data, post=post)
    return JsonResponse(build_research_post_payload(post))


@require_POST
@csrf_protect
def dashboard_login(request):
    try:
        data = parse_json_body(request.body)
    except InvalidRequestData as error:
        return JsonResponse({"detail": str(error)}, status=400)

    # 이전 프런트의 account 필드는 이메일 값일 때만 호환하고,
    # 사용자명으로 사용자를 찾는 경로는 제공하지 않습니다.
    email = str(data.get("email", data.get("account", ""))).strip().lower()
    password = str(data.get("password", ""))
    user_model = get_user_model()
    account_user = user_model.objects.filter(email__iexact=email).first()
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

    user = None
    if account_user:
        user = authenticate(
            request,
            username=account_user.get_username(),
            password=password,
        )
    if user is None:
        return JsonResponse({"detail": "이메일 또는 비밀번호를 확인해 주세요."}, status=400)

    login(request, user)
    return JsonResponse(build_user_payload(user))


@require_POST
@csrf_protect
def dashboard_signup(request):
    try:
        data = parse_json_body(request.body)
    except InvalidRequestData as error:
        return JsonResponse({"detail": str(error)}, status=400)

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
        expected_image_extension = ALLOWED_IMAGE_TYPES.get(uploaded.content_type)
        is_image = expected_image_extension == extension or (
            expected_image_extension == ".jpg" and extension == ".jpeg"
        )
        if not is_image and extension not in ALLOWED_FILE_TYPES:
            return Response({"success": 0, "message": "허용되지 않는 파일 형식입니다."}, status=400)
        if not is_image and uploaded.content_type not in ALLOWED_FILE_TYPES[extension]:
            # 확장자만 위장한 실행 파일이 저장되지 않도록 브라우저가 전달한 MIME
            # 유형과 허용 목록을 함께 비교합니다. 저장 후에는 nosniff 헤더도 적용됩니다.
            return Response(
                {"success": 0, "message": "파일 확장자와 MIME 유형이 일치하지 않습니다."},
                status=400,
            )

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
    """문의 입력은 쓰기 Serializer로 검증하고 읽기 Serializer로 응답합니다."""

    serializer_class = ContactMessageWriteSerializer
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
            **ContactMessageReadSerializer(contact).data,
            "notifications_queued": True,
        }
        return Response(response_data, status=status.HTTP_201_CREATED)
