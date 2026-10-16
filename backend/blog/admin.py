# Django 관리자 화면 기능을 가져옵니다.
from django.contrib import admin, messages
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django_smartbase_admin.admin.admin_base import SBAdmin, SBAdminTableInline
from django_smartbase_admin.admin.site import sb_admin_site
from django_smartbase_admin.engine.field import SBAdminField

# 권한이 없는 프로젝트를 저장하려 할 때 사용할 예외를 가져옵니다.
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Case, CharField, Q, Value, When
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template.loader import render_to_string
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .forms import PostAdminForm, ProjectPostAdminForm, SiteProfileAdminForm
from .tasks import enqueue_contact_reply

# 관리자 화면에 등록할 블로그 모델들을 가져옵니다.
from .models import (
    BlogAsset,
    Category,
    ContactMessage,
    Post,
    Project,
    ProjectMember,
    ProjectPost,
    SiteProfile,
    Tag,
    UserAccessStatus,
)


class UserAccessStatusInline(SBAdminTableInline):
    model = UserAccessStatus
    fk_name = "user"
    extra = 0
    max_num = 1
    can_delete = False
    readonly_fields = ("reviewed_by", "reviewed_at", "created_at", "updated_at")
    fieldsets = (
        (
            "계정 승인 및 차단",
            {
                "fields": (
                    "status",
                    "ban_reason",
                    ("reviewed_by", "reviewed_at"),
                    ("created_at", "updated_at"),
                )
            },
        ),
    )


@admin.register(User, site=sb_admin_site)
class UserSBAdmin(SBAdmin, UserAdmin):
    """SmartBase-compatible user management and autocomplete source."""

    # Django UserAdmin이 강제하는 기본 관리자 템플릿을 SmartBase 화면으로 교체합니다.
    add_form_template = "sb_admin/actions/change_form.html"
    change_user_password_template = "sb_admin/actions/change_password.html"
    list_display = UserAdmin.list_display
    sbadmin_list_display = (
        *UserAdmin.list_display,
        SBAdminField(
            name="account_status_label",
            title="계정 상태",
            annotate=Case(
                When(access_status__status="pending", then=Value("승인 대기")),
                When(access_status__status="banned", then=Value("차단")),
                default=Value("승인"),
                output_field=CharField(),
            ),
            filter_disabled=True,
        ),
    )
    list_filter = (*UserAdmin.list_filter, "access_status__status")
    inlines = (UserAccessStatusInline,)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("개인 정보", {"fields": ("first_name", "last_name", "email")}),
        (
            "권한",
            {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("중요한 일자", {"fields": ("last_login", "date_joined")}),
    )

    def get_sbadmin_fieldsets(self, request, object_id=None):
        # UserAdmin은 생성 시 password1/password2가 포함된 별도 필드셋을 사용합니다.
        return self.add_fieldsets if object_id is None else self.fieldsets

    def save_formset(self, request, form, formset, change):
        if formset.model is UserAccessStatus:
            instances = formset.save(commit=False)
            for instance in instances:
                instance.reviewed_by = request.user
                instance.reviewed_at = timezone.now()
                instance.save()
            formset.save_m2m()
            return
        super().save_formset(request, form, formset, change)


@admin.register(Group, site=sb_admin_site)
class GroupSBAdmin(SBAdmin, GroupAdmin):
    """SmartBase-compatible Django group management."""

    list_display = ("name",)
    fieldsets = (
        ("그룹 정보", {"fields": ("name", "permissions")}),
    )


def project_member_user_search(request, queryset, model, search_term, language_code):
    """Search project members by the identifiers administrators know."""
    if not search_term:
        return queryset
    return queryset.filter(
        Q(username__icontains=search_term) | Q(email__icontains=search_term)
    )


def project_member_user_label(request, user):
    """Show enough information to distinguish users with similar names."""
    return f"{user.username} · {user.email}" if user.email else user.username


class ProjectMemberUserAutocompleteMixin:
    """Configure SmartBase's user picker for project membership forms."""

    def get_autocomplete_widget(
        self, request, form_field, db_field, model, multiselect=False
    ):
        widget = super().get_autocomplete_widget(
            request, form_field, db_field, model, multiselect
        )
        if db_field.name == "user" and model is User:
            widget.search_query_lambda = project_member_user_search
            widget.label_lambda = project_member_user_label
        return widget


# 일반 블로그 데이터는 Superuser만 관리할 수 있도록 공통 권한 클래스를 만듭니다.
class SuperuserOnlyAdmin(SBAdmin):
    # 관리자 목록과 상세 화면 열람 권한을 검사합니다.
    def has_view_permission(self, request, obj=None):
        # Superuser에게만 관리자 화면 열람을 허용합니다.
        return request.user.is_superuser

    # 새 데이터 생성 권한을 검사합니다.
    def has_add_permission(self, request):
        # Superuser에게만 데이터 생성을 허용합니다.
        return request.user.is_superuser

    # 기존 데이터 수정 권한을 검사합니다.
    def has_change_permission(self, request, obj=None):
        # Superuser에게만 데이터 수정을 허용합니다.
        return request.user.is_superuser

    # 기존 데이터 삭제 권한을 검사합니다.
    def has_delete_permission(self, request, obj=None):
        # Superuser에게만 데이터 삭제를 허용합니다.
        return request.user.is_superuser


@admin.register(SiteProfile, site=sb_admin_site)
class SiteProfileAdmin(SuperuserOnlyAdmin):
    form = SiteProfileAdminForm
    fieldsets = (
        ("프로필 정보", {"fields": (("name", "role"), "bio")} ),
        ("로고", {"fields": ("logo_preview", "logo")} ),
        ("SNS 링크", {"fields": (("instagram_url", "github_url", "facebook_url"),)}),
    )
    readonly_fields = ("logo_preview",)

    def get_change_view_context(self, request, object_id):
        context = super().get_change_view_context(request, object_id)
        context["show_back_button"] = False
        return context

    def changelist_view(self, request, extra_context=None):
        SiteProfile.objects.get_or_create(pk=1)
        return HttpResponseRedirect(reverse("sb_admin:blog_siteprofile_change", args=[1]))

    @admin.display(description="현재 로고")
    def logo_preview(self, obj):
        if not obj or not obj.logo:
            return "등록된 로고가 없습니다. 공개 블로그에서는 기본 로고를 사용합니다."
        return format_html(
            '<div style="display:flex;align-items:center;gap:16px">'
            '<img src="{}?v={}" alt="현재 프로필 로고" '
            'style="width:112px;height:112px;object-fit:contain;background:#111827;'
            'border:1px solid #475569;border-radius:12px;padding:8px">'
            '<span>{}</span></div>',
            reverse("blog:site-profile-logo"),
            int(obj.updated_at.timestamp()) if obj.updated_at else 0,
            obj.logo.name.rsplit("/", 1)[-1],
        )

    def has_add_permission(self, request):
        return request.user.is_superuser and not SiteProfile.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BlogAsset, site=sb_admin_site)
class BlogAssetAdmin(SuperuserOnlyAdmin):
    list_display = ("original_name", "kind", "size", "uploaded_by", "created_at")
    list_filter = ("kind", "created_at")
    search_fields = ("original_name", "uploaded_by__username")
    readonly_fields = (
        "id",
        "file",
        "original_name",
        "content_type",
        "size",
        "kind",
        "uploaded_by",
        "created_at",
    )

    # SmartBase 상세 화면은 읽기 전용 모델도 fieldsets 정의가 필요합니다.
    fieldsets = (
        (
            "파일 정보",
            {
                "fields": (
                    "file",
                    "original_name",
                    ("kind", "content_type", "size"),
                )
            },
        ),
        (
            "업로드 정보",
            {
                "fields": (("id", "uploaded_by", "created_at"),),
                "classes": ("collapse",),
            },
        ),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# Category 모델을 Django 관리자 화면에 등록합니다.
@admin.register(Category, site=sb_admin_site)
# Category 관리자 화면 설정을 정의합니다.
class CategoryAdmin(SuperuserOnlyAdmin):
    # 카테고리 목록에 PK와 이름을 표시합니다.
    list_display = ("id", "name")

    # 카테고리 이름으로 검색할 수 있게 합니다.
    search_fields = ("name",)

    # SmartBase 추가·수정 화면에서 표시할 입력 항목을 명시합니다.
    fieldsets = (
        ("카테고리 정보", {"fields": ("name",)}),
    )


# Tag 모델을 Django 관리자 화면에 등록합니다.
@admin.register(Tag, site=sb_admin_site)
# Tag 관리자 화면 설정을 정의합니다.
class TagAdmin(SuperuserOnlyAdmin):
    # 태그 목록에 PK와 이름을 표시합니다.
    list_display = ("id", "name")

    # 태그 이름으로 검색할 수 있게 합니다.
    search_fields = ("name",)

    # SmartBase 추가·수정 화면에서 표시할 입력 항목을 명시합니다.
    fieldsets = (
        ("태그 정보", {"fields": ("name",)}),
    )


# Post 모델을 Django 관리자 화면에 등록합니다.
@admin.register(Post, site=sb_admin_site)
# 일반 블로그 게시글 관리자 화면을 정의합니다.
class PostAdmin(SuperuserOnlyAdmin):
    form = PostAdminForm
    # 게시글 목록에 자주 확인할 필드들을 표시합니다.
    list_display = (
        "id",
        "title",
        "author",
        "category",
        "status",
        "created_at",
    )
    list_display_links = ("title",)

    # 상태, 카테고리, 태그 조건으로 게시글을 필터링합니다.
    list_filter = ("status", "category", "tags")

    # 제목과 본문으로 게시글을 검색할 수 있게 합니다.
    search_fields = ("title", "content")

    # 태그를 좌우 선택 상자로 편리하게 지정할 수 있게 합니다.
    filter_horizontal = ("tags",)

    # 작성자와 생성·수정 시간은 관리자 화면에서 직접 수정하지 못하게 합니다.
    readonly_fields = ("author", "created_at", "updated_at")

    # 입력 항목을 작성 흐름에 맞춰 묶어 편집 화면의 레이아웃을 정돈합니다.
    fieldsets = (
        ("기본 정보", {"fields": ("title", ("category", "status"))}),
        ("콘텐츠", {"fields": ("content", "tags")}),
        (
            "작성 정보",
            {
                "fields": (("author", "created_at", "updated_at"),),
                "classes": ("collapse",),
            },
        ),
    )

    list_per_page = 20

    # 게시글이 저장되기 직전에 호출되는 메서드를 재정의합니다.
    def save_model(self, request, obj, form, change):
        # 새 게시글이라서 작성자가 아직 없을 때만 현재 사용자를 지정합니다.
        if not obj.author_id:
            # 현재 로그인한 Superuser를 게시글 작성자로 저장합니다.
            obj.author = request.user

        # Django의 기본 저장 로직을 실행합니다.
        super().save_model(request, obj, form, change)


# 프로젝트 상세 화면 안에서 멤버 권한을 함께 관리하기 위한 Inline을 정의합니다.
class ProjectMemberInline(ProjectMemberUserAutocompleteMixin, SBAdminTableInline):
    # Inline에서 사용할 프로젝트 멤버 모델을 지정합니다.
    model = ProjectMember

    # 사용자가 많아져도 이름이나 이메일로 빠르게 찾아 지정할 수 있게 합니다.
    autocomplete_fields = ("user",)

    # 기본으로 표시할 빈 추가 입력 줄을 없앱니다.
    extra = 0

    # 권한 부여자와 권한 부여일을 직접 수정하지 못하게 합니다.
    readonly_fields = ("granted_by", "created_at")

    # Inline에서 멤버 권한을 조회할 수 있는지 검사합니다.
    def has_view_permission(self, request, obj=None):
        # 프로젝트 권한 목록은 Superuser만 볼 수 있게 합니다.
        return request.user.is_superuser

    # Inline에서 새 멤버 권한을 추가할 수 있는지 검사합니다.
    def has_add_permission(self, request, obj=None):
        # 프로젝트 멤버 지정은 Superuser만 할 수 있게 합니다.
        return request.user.is_superuser

    # Inline에서 기존 멤버 권한을 수정할 수 있는지 검사합니다.
    def has_change_permission(self, request, obj=None):
        # 프로젝트 멤버 변경은 Superuser만 할 수 있게 합니다.
        return request.user.is_superuser

    # Inline에서 멤버 권한을 삭제할 수 있는지 검사합니다.
    def has_delete_permission(self, request, obj=None):
        # 프로젝트 멤버 권한 회수는 Superuser만 할 수 있게 합니다.
        return request.user.is_superuser


# Project 모델을 Django 관리자 화면에 등록합니다.
@admin.register(Project, site=sb_admin_site)
# 프로젝트별 멤버 권한을 적용하는 관리자 화면을 정의합니다.
class ProjectAdmin(SBAdmin):
    class Media:
        css = {"all": ("admin/project-member-manager.css",)}
        # 쿼리 버전을 올려 이전 초기화 오류가 담긴 브라우저 캐시를 확실히 갱신합니다.
        js = ("admin/project-member-manager.js?v=20261015-3",)

    # 프로젝트 목록에 관리에 필요한 필드들을 표시합니다.
    list_display = (
        "id",
        "title",
        "is_public",
        "display_order",
        "created_at",
    )
    list_display_links = ("title",)

    # 공개 여부로 프로젝트 목록을 필터링합니다.
    list_filter = ("is_public",)

    # 프로젝트 제목과 설명으로 검색할 수 있게 합니다.
    search_fields = ("title", "description")

    # 목록 화면에서 공개 여부와 표시 순서를 바로 수정할 수 있게 합니다.
    list_editable = ("is_public", "display_order")

    # 생성일과 수정일은 직접 변경할 수 없게 합니다.
    readonly_fields = ("project_member_manager", "created_at", "updated_at")

    # 프로젝트 내용, 공개 설정, 시스템 정보를 구분해 배치합니다.
    fieldsets = (
        ("프로젝트 정보", {"fields": ("title", "description")}),
        ("공개 설정", {"fields": (("is_public", "display_order"),)}),
        ("프로젝트 멤버", {"fields": ("project_member_manager",)}),
        (
            "생성 정보",
            {
                "fields": (("created_at", "updated_at"),),
                "classes": ("collapse",),
            },
        ),
    )

    list_per_page = 20

    # 멤버는 선택형 Inline 대신 검색 후 추가하는 전용 UI에서 관리합니다.
    inlines = ()

    def get_urls(self):
        custom_urls = [
            path(
                "<path:object_id>/members/popup/",
                self.admin_site.admin_view(self.member_popup),
                name="blog_project_members_popup",
            ),
            path(
                "<path:object_id>/members/search/",
                self.admin_site.admin_view(self.search_members),
                name="blog_project_members_search",
            ),
            path(
                "<path:object_id>/members/add/",
                self.admin_site.admin_view(self.add_member),
                name="blog_project_members_add",
            ),
            path(
                "<path:object_id>/members/<int:membership_id>/remove/",
                self.admin_site.admin_view(self.remove_member),
                name="blog_project_members_remove",
            ),
        ]
        return custom_urls + super().get_urls()

    def _get_member_project(self, request, object_id):
        if not request.user.is_superuser:
            raise PermissionDenied
        return self.get_object(request, object_id)

    def project_member_manager(self, obj):
        if obj is None or not obj.pk:
            return "프로젝트를 먼저 저장하면 사용자명 또는 이메일로 멤버를 검색해 추가할 수 있습니다."

        memberships = obj.memberships.select_related("user").order_by("user__username")
        return mark_safe(
            render_to_string(
                "admin/blog/project/member_manager.html",
                {
                    "project": obj,
                    "memberships": memberships,
                    "search_url": reverse(
                        "admin:blog_project_members_search", args=(obj.pk,)
                    ),
                    "popup_url": reverse(
                        "admin:blog_project_members_popup", args=(obj.pk,)
                    ),
                    "add_url": reverse("admin:blog_project_members_add", args=(obj.pk,)),
                },
            )
        )

    project_member_manager.short_description = ""

    def member_popup(self, request, object_id):
        project = self._get_member_project(request, object_id)
        if project is None:
            return HttpResponse("프로젝트를 찾을 수 없습니다.", status=404)
        return HttpResponse(
            render_to_string(
                "admin/blog/project/member_popup.html",
                {
                    "project": project,
                    "search_url": reverse(
                        "admin:blog_project_members_search", args=(project.pk,)
                    ),
                    "add_url": reverse(
                        "admin:blog_project_members_add", args=(project.pk,)
                    ),
                },
                request=request,
            )
        )

    def search_members(self, request, object_id):
        if request.method != "GET":
            return JsonResponse({"error": "허용되지 않은 요청입니다."}, status=405)
        project = self._get_member_project(request, object_id)
        if project is None:
            return JsonResponse({"error": "프로젝트를 찾을 수 없습니다."}, status=404)

        query = request.GET.get("q", "").strip()
        if not query:
            return JsonResponse({"users": []})

        # 기존 멤버를 검색 결과에서 숨기면 사용자는 검색 자체가 실패했다고 오해할 수 있습니다.
        # 검색 결과는 모두 보여주고, 이미 등록된 사용자인지만 별도로 표시합니다.
        member_ids = set(project.members.values_list("pk", flat=True))
        users = User.objects.filter(
            Q(username__icontains=query) | Q(email__icontains=query)
        ).order_by("username")[:20]
        return JsonResponse(
            {
                "users": [
                    {
                        "id": user.pk,
                        "username": user.username,
                        "email": user.email,
                        "is_member": user.pk in member_ids,
                    }
                    for user in users
                ]
            }
        )

    def add_member(self, request, object_id):
        if request.method != "POST":
            return JsonResponse({"error": "허용되지 않은 요청입니다."}, status=405)
        project = self._get_member_project(request, object_id)
        if project is None:
            return JsonResponse({"error": "프로젝트를 찾을 수 없습니다."}, status=404)

        try:
            user = User.objects.get(pk=request.POST.get("user_id"))
        except (User.DoesNotExist, TypeError, ValueError):
            return JsonResponse({"error": "사용자를 찾을 수 없습니다."}, status=404)

        membership, created = ProjectMember.objects.get_or_create(
            project=project,
            user=user,
            defaults={"granted_by": request.user},
        )
        return JsonResponse(
            {
                "created": created,
                "membership": {
                    "id": membership.pk,
                    "username": user.username,
                    "email": user.email,
                    "remove_url": reverse(
                        "admin:blog_project_members_remove",
                        args=(project.pk, membership.pk),
                    ),
                },
            }
        )

    def remove_member(self, request, object_id, membership_id):
        if request.method != "POST":
            return JsonResponse({"error": "허용되지 않은 요청입니다."}, status=405)
        project = self._get_member_project(request, object_id)
        if project is None:
            return JsonResponse({"error": "프로젝트를 찾을 수 없습니다."}, status=404)

        deleted, _ = ProjectMember.objects.filter(
            pk=membership_id, project=project
        ).delete()
        if not deleted:
            return JsonResponse({"error": "멤버를 찾을 수 없습니다."}, status=404)
        return JsonResponse({"removed": True})

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if request.user.is_superuser:
            return fieldsets
        return tuple(
            fieldset for fieldset in fieldsets if fieldset[0] != "프로젝트 멤버"
        )

    # 사용자에게 허용된 프로젝트만 목록에 표시하도록 QuerySet을 제한합니다.
    def get_queryset(self, request):
        # Django가 기본으로 생성한 프로젝트 QuerySet을 가져옵니다.
        queryset = super().get_queryset(request)

        # Superuser는 모든 프로젝트를 볼 수 있습니다.
        if request.user.is_superuser:
            # 제한하지 않은 전체 QuerySet을 반환합니다.
            return queryset

        # 일반 관리자는 자신이 멤버로 지정된 프로젝트만 볼 수 있습니다.
        return queryset.filter(members=request.user).distinct()

    # 프로젝트 목록과 상세 화면을 볼 수 있는지 검사합니다.
    def has_view_permission(self, request, obj=None):
        # Superuser는 모든 프로젝트를 볼 수 있습니다.
        if request.user.is_superuser:
            # Superuser의 조회를 허용합니다.
            return True

        # 특정 프로젝트가 없는 목록 화면에서는 멤버 프로젝트 존재 여부를 검사합니다.
        if obj is None:
            # 하나 이상의 프로젝트 권한이 있는 사용자만 목록을 볼 수 있습니다.
            return ProjectMember.objects.filter(user=request.user).exists()

        # 상세 화면에서는 해당 프로젝트의 멤버인지 검사합니다.
        return obj.members.filter(pk=request.user.pk).exists()

    # 새 프로젝트를 만들 수 있는지 검사합니다.
    def has_add_permission(self, request):
        # 새 프로젝트 생성은 Superuser만 허용합니다.
        return request.user.is_superuser

    # 프로젝트를 수정할 수 있는지 검사합니다.
    def has_change_permission(self, request, obj=None):
        # Superuser는 모든 프로젝트를 수정할 수 있습니다.
        if request.user.is_superuser:
            # Superuser의 수정을 허용합니다.
            return True

        # 목록 화면 권한 검사에서는 프로젝트 멤버 여부를 확인합니다.
        if obj is None:
            # 하나 이상의 프로젝트에 배정된 사용자에게 목록 접근을 허용합니다.
            return ProjectMember.objects.filter(user=request.user).exists()

        # 특정 프로젝트는 해당 프로젝트 멤버만 수정할 수 있습니다.
        return obj.members.filter(pk=request.user.pk).exists()

    # 프로젝트를 삭제할 수 있는지 검사합니다.
    def has_delete_permission(self, request, obj=None):
        # Superuser는 모든 프로젝트를 삭제할 수 있습니다.
        if request.user.is_superuser:
            # Superuser의 삭제를 허용합니다.
            return True

        # 삭제 대상을 알 수 없는 경우 일반 사용자에게 삭제 권한을 주지 않습니다.
        if obj is None:
            # 목록 단위의 일괄 삭제를 일반 사용자에게 허용하지 않습니다.
            return False

        # 해당 프로젝트의 멤버에게만 프로젝트 삭제를 허용합니다.
        return obj.members.filter(pk=request.user.pk).exists()

    # 프로젝트와 함께 제출된 Inline 데이터를 저장하는 방식을 재정의합니다.
    def save_formset(self, request, form, formset, change):
        # ProjectMember Inline이 아닌 다른 Inline은 기본 방식으로 저장합니다.
        if formset.model is not ProjectMember:
            # Django 기본 Inline 저장 로직을 실행합니다.
            return super().save_formset(request, form, formset, change)

        # 프로젝트 멤버 권한은 Superuser만 저장할 수 있습니다.
        if not request.user.is_superuser:
            # 권한이 없는 저장 요청을 거부합니다.
            raise PermissionDenied

        # 아직 DB에 저장하지 않은 Inline 객체들을 가져옵니다.
        memberships = formset.save(commit=False)

        # Inline에서 삭제 표시된 기존 권한들을 순회합니다.
        for membership in formset.deleted_objects:
            # 선택된 프로젝트 멤버 권한을 삭제합니다.
            membership.delete()

        # 새로 만들거나 변경된 프로젝트 멤버 권한을 순회합니다.
        for membership in memberships:
            # 신규 권한이고 권한 부여자가 비어 있으면 현재 Superuser를 기록합니다.
            if not membership.granted_by_id:
                # 현재 로그인한 Superuser를 권한 부여자로 지정합니다.
                membership.granted_by = request.user

            # 프로젝트 멤버 권한을 DB에 저장합니다.
            membership.save()

        # Inline에 다대다 필드가 생길 경우를 대비해 다대다 관계도 저장합니다.
        formset.save_m2m()


# ProjectMember 모델을 별도 관리자 목록에도 등록합니다.
@admin.register(ProjectMember, site=sb_admin_site)
# 프로젝트 권한 내역은 Superuser만 관리하도록 설정합니다.
class ProjectMemberAdmin(ProjectMemberUserAutocompleteMixin, SuperuserOnlyAdmin):
    # 권한 목록에 프로젝트, 사용자, 부여자, 부여일을 표시합니다.
    list_display = ("id", "project", "user", "granted_by", "created_at")

    # 프로젝트와 사용자 기준으로 권한 목록을 필터링합니다.
    list_filter = ("project", "user")

    # 프로젝트 제목과 사용자 이름으로 권한을 검색할 수 있게 합니다.
    search_fields = (
        "project__title",
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    )

    # 프로젝트와 사용자를 검색형 선택 상자로 제공합니다.
    autocomplete_fields = ("project", "user")

    # 권한 부여자와 권한 부여일은 직접 변경하지 못하게 합니다.
    readonly_fields = ("granted_by", "created_at")

    fieldsets = (
        ("프로젝트 권한", {"fields": (("project", "user"),)}),
        (
            "권한 부여 정보",
            {"fields": (("granted_by", "created_at"),), "classes": ("collapse",)},
        ),
    )

    # 프로젝트 멤버 권한 저장 직전에 호출되는 메서드를 재정의합니다.
    def save_model(self, request, obj, form, change):
        # 신규 권한이라서 권한 부여자가 없을 때만 현재 사용자를 지정합니다.
        if not obj.granted_by_id:
            # 현재 로그인한 Superuser를 권한 부여자로 기록합니다.
            obj.granted_by = request.user

        # Django의 기본 저장 로직을 실행합니다.
        super().save_model(request, obj, form, change)


# ProjectPost 모델을 Django 관리자 화면에 등록합니다.
@admin.register(ProjectPost, site=sb_admin_site)
# 프로젝트별 권한을 적용하는 프로젝트 글 관리자 화면을 정의합니다.
class ProjectPostAdmin(SBAdmin):
    form = ProjectPostAdminForm
    # 프로젝트 글 목록에 관리에 필요한 필드들을 표시합니다.
    list_display = (
        "id",
        "title",
        "project",
        "author",
        "is_public",
        "created_at",
    )
    list_display_links = ("title",)

    # 프로젝트와 공개 여부 및 태그로 글을 필터링합니다.
    list_filter = ("project", "is_public", "tags")

    # 제목과 본문으로 프로젝트 글을 검색할 수 있게 합니다.
    search_fields = ("title", "content")

    # 태그를 좌우 선택 상자로 지정할 수 있게 합니다.
    filter_horizontal = ("tags",)

    # 작성자와 생성·수정 시간은 직접 변경하지 못하게 합니다.
    readonly_fields = ("author", "created_at", "updated_at")

    # 프로젝트 선택부터 본문 작성까지 자연스러운 순서로 필드를 배치합니다.
    fieldsets = (
        ("기본 정보", {"fields": ("project", "title", "is_public")}),
        ("콘텐츠", {"fields": ("content", "tags")}),
        (
            "작성 정보",
            {
                "fields": (("author", "created_at", "updated_at"),),
                "classes": ("collapse",),
            },
        ),
    )

    list_per_page = 20

    # 현재 사용자에게 허용된 프로젝트 글만 목록에 표시합니다.
    def get_queryset(self, request):
        # Django 기본 프로젝트 글 QuerySet을 가져옵니다.
        queryset = super().get_queryset(request)

        # Superuser는 모든 프로젝트 글을 볼 수 있습니다.
        if request.user.is_superuser:
            # 제한하지 않은 전체 QuerySet을 반환합니다.
            return queryset

        # 일반 관리자는 자신이 멤버인 프로젝트의 글만 볼 수 있습니다.
        return queryset.filter(project__members=request.user).distinct()

    # 프로젝트 선택 필드에 허용된 프로젝트만 표시합니다.
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # 현재 처리 중인 필드가 프로젝트 외래키인지 확인합니다.
        if db_field.name == "project" and not request.user.is_superuser:
            # 일반 사용자에게는 배정받은 프로젝트만 선택지로 제공합니다.
            kwargs["queryset"] = Project.objects.filter(members=request.user).distinct()

        # Django 기본 외래키 폼 필드 생성 로직을 실행합니다.
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # 프로젝트 글 관리자 화면을 볼 수 있는지 검사합니다.
    def has_view_permission(self, request, obj=None):
        # Superuser는 모든 프로젝트 글을 볼 수 있습니다.
        if request.user.is_superuser:
            # Superuser의 조회를 허용합니다.
            return True

        # 목록 화면에서는 하나 이상의 프로젝트 권한이 있는지 검사합니다.
        if obj is None:
            # 배정된 프로젝트가 있는 사용자만 목록을 볼 수 있습니다.
            return ProjectMember.objects.filter(user=request.user).exists()

        # 상세 화면에서는 글이 속한 프로젝트의 멤버인지 검사합니다.
        return obj.project.members.filter(pk=request.user.pk).exists()

    # 새 프로젝트 글을 만들 수 있는지 검사합니다.
    def has_add_permission(self, request):
        # Superuser는 모든 프로젝트에 글을 작성할 수 있습니다.
        if request.user.is_superuser:
            # Superuser의 글 생성을 허용합니다.
            return True

        # 배정된 프로젝트가 하나라도 있는 사용자에게 글 생성을 허용합니다.
        return ProjectMember.objects.filter(user=request.user).exists()

    # 프로젝트 글을 수정할 수 있는지 검사합니다.
    def has_change_permission(self, request, obj=None):
        # Superuser는 모든 프로젝트 글을 수정할 수 있습니다.
        if request.user.is_superuser:
            # Superuser의 수정을 허용합니다.
            return True

        # 목록 화면에서는 프로젝트 멤버 권한이 있는지 검사합니다.
        if obj is None:
            # 배정된 프로젝트가 있는 사용자에게 목록 접근을 허용합니다.
            return ProjectMember.objects.filter(user=request.user).exists()

        # 특정 글은 해당 프로젝트 멤버만 수정할 수 있습니다.
        return obj.project.members.filter(pk=request.user.pk).exists()

    # 프로젝트 글을 삭제할 수 있는지 검사합니다.
    def has_delete_permission(self, request, obj=None):
        # Superuser는 모든 프로젝트 글을 삭제할 수 있습니다.
        if request.user.is_superuser:
            # Superuser의 삭제를 허용합니다.
            return True

        # 삭제할 글이 정해지지 않은 경우 일반 사용자에게 권한을 주지 않습니다.
        if obj is None:
            # 일반 사용자의 일괄 삭제를 차단합니다.
            return False

        # 특정 글은 해당 프로젝트 멤버만 삭제할 수 있습니다.
        return obj.project.members.filter(pk=request.user.pk).exists()

    # 프로젝트 글이 저장되기 직전에 추가 권한 검사를 수행합니다.
    def save_model(self, request, obj, form, change):
        # Superuser가 아니라면 선택한 프로젝트의 멤버인지 다시 검사합니다.
        if not request.user.is_superuser:
            # 선택한 프로젝트에 현재 사용자의 멤버 권한이 있는지 확인합니다.
            is_member = obj.project.members.filter(pk=request.user.pk).exists()

            # 프로젝트 멤버가 아니라면 위조된 저장 요청을 거부합니다.
            if not is_member:
                # Django 권한 거부 예외를 발생시킵니다.
                raise PermissionDenied

        # 새 프로젝트 글이라서 작성자가 없을 때 현재 사용자를 지정합니다.
        if not obj.author_id:
            # 현재 로그인한 사용자를 프로젝트 글 작성자로 저장합니다.
            obj.author = request.user

        # Django의 기본 저장 로직을 실행합니다.
        super().save_model(request, obj, form, change)


@admin.register(ContactMessage, site=sb_admin_site)
class ContactMessageAdmin(SuperuserOnlyAdmin):
    """접수된 문의와 이메일 답변 정보를 관리합니다."""

    list_display = (
        "id",
        "name",
        "email",
        "live_status",
        "created_at",
        "replied_at",
    )
    list_display_links = ("name",)
    list_filter = ("status", "created_at", "replied_at")
    search_fields = ("name", "email", "message", "reply")
    readonly_fields = (
        "name",
        "email",
        "message",
        "delivery_status_tracker",
        "replied_by",
        "replied_at",
        "receipt_sent_at",
        "email_sent_at",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        ("문의자", {"fields": (("name", "email"),)}),
        ("문의 내용", {"fields": ("message",)}),
        ("답변", {"fields": ("status", "reply", "delivery_status_tracker")}),
        (
            "처리 정보",
            {
                "fields": (
                    ("replied_by", "replied_at"),
                    ("receipt_sent_at", "email_sent_at"),
                    ("created_at", "updated_at"),
                ),
                "classes": ("collapse",),
            },
        ),
    )
    ordering = ("-created_at",)
    list_per_page = 20

    def has_add_permission(self, request):
        # 문의는 공개 Contact 폼을 통해서만 생성합니다.
        return False

    def get_urls(self):
        """현재 문의의 메일 발송 상태를 조회하는 관리자 전용 URL을 추가합니다."""
        custom_urls = [
            path(
                "<path:object_id>/delivery-status/",
                self.admin_site.admin_view(self.delivery_status),
                name="blog_contactmessage_delivery_status",
            ),
        ]
        return custom_urls + super().get_urls()

    @admin.display(description="이메일 발송 상태")
    def delivery_status_tracker(self, obj):
        """프런트 폴링에 필요한 URL과 현재 발송 상태를 안전하게 전달합니다."""
        if obj is None or not obj.pk:
            return "답변을 저장하면 이메일 발송 상태를 확인할 수 있습니다."

        return self._render_delivery_status(
            obj,
            self._delivery_status_message(obj),
            refresh_on_complete=True,
        )

    @admin.display(description="상태", ordering="status")
    def live_status(self, obj_or_id, value=None, **additional_data):
        """Django와 SmartBase 양쪽 호출 규격으로 실시간 상태 셀을 표시합니다."""
        # 기본 Django 관리자는 모델 객체를 넘기지만 SmartBase 목록 JSON은 객체 ID와
        # 계산된 값을 따로 넘깁니다. 두 화면에서 같은 메서드를 안전하게 재사용하기
        # 위해 ID로 받은 경우에만 상태에 필요한 최소 필드를 다시 조회합니다.
        if isinstance(obj_or_id, ContactMessage):
            obj = obj_or_id
        else:
            obj = ContactMessage.objects.only("id", "status").get(pk=obj_or_id)
        return self._render_delivery_status(
            obj,
            obj.get_status_display(),
            refresh_on_complete=False,
        )

    def _render_delivery_status(self, obj, label, *, refresh_on_complete):
        """상세 화면과 목록에서 함께 사용하는 실시간 상태 요소를 만듭니다."""
        status_url = reverse(
            "admin:blog_contactmessage_delivery_status",
            args=[obj.pk],
        )
        return format_html(
            '<span data-contact-delivery-status data-status-url="{}" '
            'data-status="{}" data-refresh-on-complete="{}" '
            'role="status" aria-live="polite">{}</span>',
            status_url,
            obj.status,
            "true" if refresh_on_complete else "false",
            label,
        )

    def delivery_status(self, request, object_id):
        """메일 발송 완료 여부만 반환해 문의 상세 화면이 즉시 갱신되게 합니다."""
        contact = self.get_object(request, object_id)
        if contact is None:
            return JsonResponse({"message": "문의를 찾을 수 없습니다."}, status=404)
        if not self.has_view_or_change_permission(request, contact):
            raise PermissionDenied

        return JsonResponse(
            {
                "status": contact.status,
                "status_label": contact.get_status_display(),
                "is_complete": contact.status == ContactMessage.Status.REPLIED,
                "message": self._delivery_status_message(contact),
                "email_sent_at": (
                    contact.email_sent_at.isoformat()
                    if contact.email_sent_at
                    else None
                ),
            }
        )

    @staticmethod
    def _delivery_status_message(contact):
        """관리자가 기술 용어 없이 현재 처리 단계를 이해할 문구를 만듭니다."""
        if contact.status == ContactMessage.Status.REPLIED:
            return "이메일 발송이 완료되어 답변 완료 상태입니다."
        if contact.status == ContactMessage.Status.IN_PROGRESS:
            return "답변 이메일을 발송하고 있습니다. 완료되면 자동으로 갱신됩니다."
        return "아직 답변 이메일을 발송하지 않았습니다."

    def save_model(self, request, obj, form, change):
        should_send = bool(obj.reply.strip()) and (
            "reply" in form.changed_data
            or (
                obj.email_sent_at is None
                and obj.status != ContactMessage.Status.IN_PROGRESS
            )
        )
        super().save_model(request, obj, form, change)

        if not should_send:
            return

        ContactMessage.objects.filter(pk=obj.pk).update(
            status=ContactMessage.Status.IN_PROGRESS,
            replied_by=request.user,
        )
        obj.status = ContactMessage.Status.IN_PROGRESS
        obj.replied_by = request.user
        transaction.on_commit(
            lambda: enqueue_contact_reply(obj.pk, request.user.pk)
        )
        self.message_user(
            request,
            "답변을 저장했으며 이메일 전송을 백그라운드에서 시작했습니다.",
            messages.SUCCESS,
        )
