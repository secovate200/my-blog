from django.shortcuts import render
from rest_framework.generics import ListAPIView, RetrieveAPIView
from .models import Post
from .serializer import PostSerializer

class PostListApiView(ListAPIView):
    """
    공개된 게시글 목록조회 API
    """
    serializer_class = PostSerializer
    def get_queryset(self):
        # status가 PUBLISHED인 글만 가져옵니다.
        # 초안은 방문자에게 보여주지 않습니다.
        return (
            Post.objects
            .filter(status=Post.Status.PUBLISHED)
            .select_related("category", "author")
            .prefetch_related("tags")
            .order_by("-created_at")
        )

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