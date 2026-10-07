"""Navigation and role configuration for the SmartBase admin site."""

from django_smartbase_admin.engine.configuration import (
    SBAdminConfigurationBase,
    SBAdminRoleConfiguration,
)
from django_smartbase_admin.engine.menu_item import SBAdminMenuItem
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
    def get_configuration_for_roles(self, user_roles):
        return configuration
