# Django 관리자 화면 기능을 가져옵니다.
from django.contrib import admin, messages

# 권한이 없는 프로젝트를 저장하려 할 때 사용할 예외를 가져옵니다.
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from .notifications import send_contact_reply

# 관리자 화면에 등록할 블로그 모델들을 가져옵니다.
from .models import (
    Category,
    ContactMessage,
    Post,
    Project,
    ProjectMember,
    ProjectPost,
    Tag,
)


# 일반 블로그 데이터는 Superuser만 관리할 수 있도록 공통 권한 클래스를 만듭니다.
class SuperuserOnlyAdmin(admin.ModelAdmin):
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


# Category 모델을 Django 관리자 화면에 등록합니다.
@admin.register(Category)
# Category 관리자 화면 설정을 정의합니다.
class CategoryAdmin(SuperuserOnlyAdmin):
    # 카테고리 목록에 PK와 이름을 표시합니다.
    list_display = ("id", "name")

    # 카테고리 이름으로 검색할 수 있게 합니다.
    search_fields = ("name",)


# Tag 모델을 Django 관리자 화면에 등록합니다.
@admin.register(Tag)
# Tag 관리자 화면 설정을 정의합니다.
class TagAdmin(SuperuserOnlyAdmin):
    # 태그 목록에 PK와 이름을 표시합니다.
    list_display = ("id", "name")

    # 태그 이름으로 검색할 수 있게 합니다.
    search_fields = ("name",)


# Post 모델을 Django 관리자 화면에 등록합니다.
@admin.register(Post)
# 일반 블로그 게시글 관리자 화면을 정의합니다.
class PostAdmin(SuperuserOnlyAdmin):
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
class ProjectMemberInline(admin.TabularInline):
    # Inline에서 사용할 프로젝트 멤버 모델을 지정합니다.
    model = ProjectMember

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
@admin.register(Project)
# 프로젝트별 멤버 권한을 적용하는 관리자 화면을 정의합니다.
class ProjectAdmin(admin.ModelAdmin):
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
    readonly_fields = ("created_at", "updated_at")

    # 프로젝트 내용, 공개 설정, 시스템 정보를 구분해 배치합니다.
    fieldsets = (
        ("프로젝트 정보", {"fields": ("title", "description")}),
        ("공개 설정", {"fields": (("is_public", "display_order"),)}),
        (
            "생성 정보",
            {
                "fields": (("created_at", "updated_at"),),
                "classes": ("collapse",),
            },
        ),
    )

    list_per_page = 20

    # Superuser에게만 멤버 관리 Inline을 보여줍니다.
    inlines = (ProjectMemberInline,)

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

    # 현재 사용자에게 보여줄 Inline 목록을 결정합니다.
    def get_inlines(self, request, obj=None):
        # Superuser에게만 프로젝트 멤버 관리 Inline을 제공합니다.
        if request.user.is_superuser:
            # 등록된 멤버 관리 Inline 목록을 반환합니다.
            return self.inlines

        # 일반 프로젝트 멤버에게는 권한 관리 Inline을 노출하지 않습니다.
        return ()

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
@admin.register(ProjectMember)
# 프로젝트 권한 내역은 Superuser만 관리하도록 설정합니다.
class ProjectMemberAdmin(SuperuserOnlyAdmin):
    # 권한 목록에 프로젝트, 사용자, 부여자, 부여일을 표시합니다.
    list_display = ("id", "project", "user", "granted_by", "created_at")

    # 프로젝트와 사용자 기준으로 권한 목록을 필터링합니다.
    list_filter = ("project", "user")

    # 프로젝트 제목과 사용자 이름으로 권한을 검색할 수 있게 합니다.
    search_fields = ("project__title", "user__username")

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
@admin.register(ProjectPost)
# 프로젝트별 권한을 적용하는 프로젝트 글 관리자 화면을 정의합니다.
class ProjectPostAdmin(admin.ModelAdmin):
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


@admin.register(ContactMessage)
class ContactMessageAdmin(SuperuserOnlyAdmin):
    """접수된 문의와 이메일 답변 정보를 관리합니다."""

    list_display = (
        "id",
        "name",
        "email",
        "status",
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
        ("답변", {"fields": ("status", "reply")}),
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

    def save_model(self, request, obj, form, change):
        should_send = bool(obj.reply.strip()) and (
            "reply" in form.changed_data or obj.email_sent_at is None
        )
        super().save_model(request, obj, form, change)

        if not should_send:
            return

        if send_contact_reply(obj):
            sent_at = timezone.now()
            ContactMessage.objects.filter(pk=obj.pk).update(
                status=ContactMessage.Status.REPLIED,
                replied_by=request.user,
                replied_at=sent_at,
                email_sent_at=sent_at,
            )
            obj.status = ContactMessage.Status.REPLIED
            obj.replied_by = request.user
            obj.replied_at = sent_at
            obj.email_sent_at = sent_at
            self.message_user(request, "답변 이메일을 전송했습니다.", messages.SUCCESS)
        else:
            self.message_user(
                request,
                "답변은 저장했지만 이메일 전송에 실패했습니다. SMTP 설정을 확인해 주세요.",
                messages.WARNING,
            )
