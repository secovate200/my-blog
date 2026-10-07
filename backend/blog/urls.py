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
    dashboard_csrf,
    dashboard_current_user,
    dashboard_login,
    dashboard_signup,
    dashboard_logout,
    dashboard_summary,
    dashboard_posts,
    dashboard_post_detail,
    dashboard_categories,
    dashboard_projects,
    dashboard_research_posts,
    dashboard_research_post_detail,
)


app_name = "blog"

urlpatterns = [
    path("auth/csrf/", dashboard_csrf, name="dashboard-csrf"),
    path("auth/login/", dashboard_login, name="dashboard-login"),
    path("auth/signup/", dashboard_signup, name="dashboard-signup"),
    path("auth/logout/", dashboard_logout, name="dashboard-logout"),
    path("auth/me/", dashboard_current_user, name="dashboard-current-user"),
    path("dashboard/summary/", dashboard_summary, name="dashboard-summary"),
    path("dashboard/posts/", dashboard_posts, name="dashboard-posts"),
    path("dashboard/posts/<int:pk>/", dashboard_post_detail, name="dashboard-post-detail"),
    path("dashboard/categories/", dashboard_categories, name="dashboard-categories"),
    path("dashboard/projects/", dashboard_projects, name="dashboard-projects"),
    path("dashboard/projects/<int:project_pk>/posts/", dashboard_research_posts, name="dashboard-research-posts"),
    path("dashboard/research-posts/<int:pk>/", dashboard_research_post_detail, name="dashboard-research-post-detail"),
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
