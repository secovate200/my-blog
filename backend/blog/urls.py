from django.urls import path

from .views import PostDetailAPIView, PostListApiView


app_name = "blog"

urlpatterns = [
    path("posts/", PostListApiView.as_view(), name="post-list"),
    path("posts/<int:pk>/", PostDetailAPIView.as_view(), name="post-detail"),
]