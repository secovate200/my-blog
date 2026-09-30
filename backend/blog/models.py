from django.conf import settings
from django.db import models


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
