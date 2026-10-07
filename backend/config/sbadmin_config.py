"""Navigation and role configuration for the SmartBase admin site."""

from django_smartbase_admin.engine.configuration import (
    SBAdminConfigurationBase,
    SBAdminRoleConfiguration,
)
from django_smartbase_admin.engine.menu_item import SBAdminMenuItem
from django_smartbase_admin.models import ColorScheme
from django_smartbase_admin.views.dashboard_view import SBAdminDashboardView

from .dashboard import MyBlogOverviewWidget


blog_menu = SBAdminMenuItem(
    label="블로그",
    icon="Write",
    sub_items=[
        SBAdminMenuItem(view_id="blog_post"),
        SBAdminMenuItem(view_id="blog_category"),
        SBAdminMenuItem(view_id="blog_tag"),
        SBAdminMenuItem(view_id="blog_blogasset"),
    ],
)

project_menu = SBAdminMenuItem(
    label="프로젝트",
    icon="Box",
    sub_items=[
        SBAdminMenuItem(view_id="blog_project"),
        SBAdminMenuItem(view_id="blog_projectpost"),
        SBAdminMenuItem(view_id="blog_projectmember"),
    ],
)

configuration = SBAdminRoleConfiguration(
    admin_title="My Blog 관리",
    default_color_scheme=ColorScheme.LIGHT,
    default_view=SBAdminMenuItem(view_id="dashboard"),
    registered_views=[
        SBAdminDashboardView(
            widgets=[MyBlogOverviewWidget()],
            title="My Blog 대시보드",
        ),
    ],
    menu_items=[
        SBAdminMenuItem(
            view_id="dashboard",
            label="대시보드",
            icon="All-application",
        ),
        blog_menu,
        project_menu,
        SBAdminMenuItem(view_id="blog_contactmessage", icon="Mail"),
        SBAdminMenuItem(
            label="계정",
            icon="User-business",
            sub_items=[
                SBAdminMenuItem(view_id="auth_user"),
                SBAdminMenuItem(view_id="auth_group"),
            ],
        ),
    ],
)


class SBAdminConfiguration(SBAdminConfigurationBase):
    @classmethod
    def get_user_config(cls, request):
        user_config = super().get_user_config(request)
        shared_theme = request.COOKIES.get("secovate-theme")
        if user_config and shared_theme in {ColorScheme.LIGHT.value, ColorScheme.DARK.value}:
            if user_config.color_scheme != shared_theme:
                user_config.color_scheme = shared_theme
                user_config.save(update_fields=["color_scheme"])
        elif user_config and user_config.color_scheme == ColorScheme.AUTO:
            user_config.color_scheme = ColorScheme.LIGHT
            user_config.save(update_fields=["color_scheme"])
        return user_config

    def get_configuration_for_roles(self, user_roles):
        return configuration
