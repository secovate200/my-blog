from django.urls import path

from .views import (
    ContactMessageCreateAPIView,
    PostDetailAPIView,
    PostListApiView,
    ProjectDetailAPIView,
    ProjectListAPIView,
    ProjectPostDetailAPIView,
)


app_name = "blog"

urlpatterns = [
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
