from pathlib import Path

from django.db.models import Count, Prefetch, Q
from django.http import FileResponse, Http404
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
from .models import BlogAsset, Post, Project, ProjectPost
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
