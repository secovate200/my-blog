from django.conf import settings
from django.db import models
import uuid


def asset_upload_path(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"blog-assets/{instance.id}.{extension}"


class UserAccessStatus(models.Model):
    """회원가입 승인과 이용 제한 상태를 Django 사용자와 분리해 기록합니다."""

    class Status(models.TextChoices):
        PENDING = "pending", "승인 대기"
        APPROVED = "approved", "승인"
        BANNED = "banned", "차단"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="사용자",
        related_name="access_status",
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        "계정 상태", max_length=20, choices=Status.choices, default=Status.PENDING
    )
    ban_reason = models.TextField("차단 사유", blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="처리 관리자",
        related_name="reviewed_access_statuses",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    reviewed_at = models.DateTimeField("처리일", null=True, blank=True)
    created_at = models.DateTimeField("가입일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        verbose_name = "계정 접근 상태"
        verbose_name_plural = "계정 접근 상태"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        should_be_active = self.status == self.Status.APPROVED
        type(self.user).objects.filter(pk=self.user_id).exclude(
            is_active=should_be_active
        ).update(is_active=should_be_active)

    def __str__(self):
        return f"{self.user} - {self.get_status_display()}"


class Category(models.Model):
    """게시글을 주제별로 분류합니다."""

    name = models.CharField("이름", max_length=200, unique=True)

    class Meta:
        verbose_name = "카테고리"
        verbose_name_plural = "카테고리"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Tag(models.Model):
    """여러 게시글에서 재사용할 수 있는 태그입니다."""

    name = models.CharField("이름", max_length=100, unique=True)

    class Meta:
        verbose_name = "태그"
        verbose_name_plural = "태그"
        ordering = ["name"]

    def __str__(self):
        return self.name


class BlogAsset(models.Model):
    class Kind(models.TextChoices):
        IMAGE = "image", "이미지"
        FILE = "file", "첨부파일"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField("파일", upload_to=asset_upload_path)
    original_name = models.CharField("원본 파일명", max_length=255)
    content_type = models.CharField("MIME 유형", max_length=100)
    size = models.PositiveBigIntegerField("크기")
    kind = models.CharField("종류", max_length=10, choices=Kind.choices)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="업로더",
        on_delete=models.PROTECT,
        related_name="blog_assets",
    )
    created_at = models.DateTimeField("업로드일", auto_now_add=True)

    class Meta:
        verbose_name = "게시글 파일"
        verbose_name_plural = "게시글 파일"
        ordering = ["-created_at"]

    def __str__(self):
        return self.original_name


class Post(models.Model):
    """Superuser가 작성하고 공개 상태를 관리하는 블로그 게시글입니다."""

    class Status(models.TextChoices):
        DRAFT = "0", "Draft"
        PUBLISHED = "1", "Publish"

    title = models.CharField("제목", max_length=200)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="작성자",
        related_name="posts",
        on_delete=models.PROTECT,
        editable=False,
    )
    category = models.ForeignKey(
        Category,
        verbose_name="카테고리",
        related_name="posts",
        on_delete=models.PROTECT,
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name="태그",
        related_name="posts",
        blank=True,
    )
    content = models.TextField("본문")
    status = models.CharField(
        "상태",
        max_length=1,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_at = models.DateTimeField("작성일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        verbose_name = "게시글"
        verbose_name_plural = "게시글"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Project(models.Model):
    """공개하거나 특정 사용자에게 관리 권한을 부여할 수 있는 프로젝트입니다."""

    title = models.CharField("제목", max_length=200)
    description = models.TextField("설명")
    is_public = models.BooleanField("공개 여부", default=False)
    display_order = models.PositiveIntegerField("표시 순서", default=0)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name="관리 멤버",
        related_name="managed_projects",
        through="ProjectMember",
        through_fields=("project", "user"),
        blank=True,
    )
    created_at = models.DateTimeField("생성일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        verbose_name = "프로젝트"
        verbose_name_plural = "프로젝트"
        ordering = ["display_order", "-created_at"]

    def __str__(self):
        return self.title


class ProjectMember(models.Model):
    """Superuser가 사용자에게 부여한 프로젝트별 관리 권한입니다."""

    project = models.ForeignKey(
        Project,
        verbose_name="프로젝트",
        related_name="memberships",
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="사용자",
        related_name="project_memberships",
        on_delete=models.CASCADE,
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="권한 부여자",
        related_name="granted_project_memberships",
        on_delete=models.PROTECT,
        editable=False,
    )
    created_at = models.DateTimeField("권한 부여일", auto_now_add=True)

    class Meta:
        verbose_name = "프로젝트 멤버"
        verbose_name_plural = "프로젝트 멤버"
        ordering = ["project", "user"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "user"],
                name="unique_project_member",
            )
        ]

    def __str__(self):
        return f"{self.project} - {self.user}"


class ProjectPost(models.Model):
    """프로젝트 안에서 별도로 관리하는 게시글입니다."""

    project = models.ForeignKey(
        Project,
        verbose_name="프로젝트",
        related_name="posts",
        on_delete=models.CASCADE,
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="작성자",
        related_name="project_posts",
        on_delete=models.PROTECT,
        editable=False,
    )
    title = models.CharField("제목", max_length=200)
    content = models.TextField("본문")
    tags = models.ManyToManyField(
        Tag,
        verbose_name="태그",
        related_name="project_posts",
        blank=True,
    )
    is_public = models.BooleanField("공개 여부", default=False)
    created_at = models.DateTimeField("작성일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        verbose_name = "프로젝트 글"
        verbose_name_plural = "프로젝트 글"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class ContactMessage(models.Model):
    """블로그 방문자가 남긴 문의와 관리자의 이메일 답변을 보관합니다."""

    class Status(models.TextChoices):
        NEW = "new", "새 문의"
        IN_PROGRESS = "in_progress", "확인 중"
        REPLIED = "replied", "답변 완료"

    name = models.CharField("이름", max_length=50)
    email = models.EmailField("이메일", max_length=254)
    message = models.TextField("문의 내용", max_length=2000)
    status = models.CharField(
        "상태",
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )
    reply = models.TextField("답변 내용", max_length=5000, blank=True)
    replied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="답변자",
        related_name="replied_contact_messages",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
    )
    replied_at = models.DateTimeField("답변일", null=True, blank=True)
    receipt_sent_at = models.DateTimeField("접수 메일 발송일", null=True, blank=True)
    email_sent_at = models.DateTimeField("메일 발송일", null=True, blank=True)
    created_at = models.DateTimeField("접수일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        verbose_name = "문의"
        verbose_name_plural = "문의"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.email})"
