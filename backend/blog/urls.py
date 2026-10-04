from django.urls import path

from .views import (
    BlogAssetContentAPIView,
    BlogAssetDownloadAPIView,
    BlogAssetUploadAPIView,
    ContactMessageCreateAPIView,
    PostDetailAPIView,
    PostListApiView,
    ProjectDetailAPIView,
    ProjectListAPIView,
    ProjectPostDetailAPIView,
)


app_name = "blog"

urlpatterns = [
    path("assets/upload/", BlogAssetUploadAPIView.as_view(), name="asset-upload"),
    path("assets/<uuid:pk>/content/", BlogAssetContentAPIView.as_view(), name="asset-content"),
    path("assets/<uuid:pk>/download/", BlogAssetDownloadAPIView.as_view(), name="asset-download"),
    path("posts/", PostListApiView.as_view(), name="post-list"),
    path("posts/<int:pk>/", PostDetailAPIView.as_view(), name="post-detail"),
    path("projects/", ProjectListAPIView.as_view(), name="project-list"),
    path("projects/<int:pk>/", ProjectDetailAPIView.as_view(), name="project-detail"),
    path(
        "projects/<int:project_pk>/posts/<int:pk>/",
        ProjectPostDetailAPIView.as_view(),
        name="project-post-detail",
    ),
    path("contact/", ContactMessageCreateAPIView.as_view(), name="contact-create"),
]
