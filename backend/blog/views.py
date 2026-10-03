from django.db.models import Count, Prefetch, Q
from rest_framework import status
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from .models import Post, Project, ProjectPost
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
