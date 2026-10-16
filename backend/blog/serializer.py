"""공개 API의 읽기 표현과 입력 검증 Serializer를 분리해 정의합니다."""

from rest_framework import serializers

from .models import ContactMessage, Post, Project, ProjectPost, SiteProfile


class SiteProfileReadSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = SiteProfile
        fields = [
            "name", "role", "bio", "logo_url",
            "instagram_url", "github_url", "facebook_url",
        ]

    def get_logo_url(self, obj):
        return "/blog/profile/logo/" if obj.logo else None


class PostReadSerializer(serializers.ModelSerializer):
    """공개 게시글의 관계 객체를 사람이 읽기 좋은 이름으로 직렬화합니다."""

    category = serializers.StringRelatedField(read_only=True)
    tags = serializers.StringRelatedField(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Post
        fields = [
            "id",
            "title",
            "author",
            "category",
            "tags",
            "content",
            "status",
            "created_at",
            "updated_at",
        ]


class ProjectPostReadSerializer(serializers.ModelSerializer):
    """공개 프로젝트 글과 소속 프로젝트 이름을 함께 반환합니다."""

    tags = serializers.StringRelatedField(many=True, read_only=True)
    project_title = serializers.CharField(source="project.title", read_only=True)

    class Meta:
        model = ProjectPost
        fields = [
            "id",
            "project",
            "project_title",
            "title",
            "content",
            "tags",
            "created_at",
            "updated_at",
        ]


class ProjectListReadSerializer(serializers.ModelSerializer):
    """공개 프로젝트 목록에 공개 글 수와 태그 요약을 포함합니다."""

    post_count = serializers.IntegerField(read_only=True)
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "title",
            "description",
            "tags",
            "post_count",
            "created_at",
            "updated_at",
        ]

    def get_tags(self, obj) -> list[str]:
        """공개 글에서 실제 사용 중인 태그만 중복 없이 반환합니다."""

        # 비공개 글의 태그가 목록 필터에 노출되면 글 존재를 추측할 수 있으므로
        # 공개 글로 범위를 제한한 뒤 데이터베이스에서 중복 제거와 정렬을 수행합니다.
        return list(
            obj.posts.filter(is_public=True)
            .values_list("tags__name", flat=True)
            .exclude(tags__name__isnull=True)
            .distinct()
            .order_by("tags__name")
        )


class ProjectDetailReadSerializer(ProjectListReadSerializer):
    """프로젝트 요약에 미리 필터링된 공개 글 목록을 덧붙입니다."""

    posts = ProjectPostReadSerializer(many=True, read_only=True)

    class Meta(ProjectListReadSerializer.Meta):
        fields = [*ProjectListReadSerializer.Meta.fields, "posts"]


class ContactMessageWriteSerializer(serializers.ModelSerializer):
    """방문자 문의 입력만 검증하며 서버 관리 필드는 받지 않습니다."""

    class Meta:
        model = ContactMessage
        fields = ["name", "email", "message"]


class ContactMessageReadSerializer(serializers.ModelSerializer):
    """문의 접수 뒤 클라이언트에 돌려줄 안전한 필드만 직렬화합니다."""

    class Meta:
        model = ContactMessage
        fields = ["id", "name", "email", "message", "created_at"]
        read_only_fields = fields


PostSerializer = PostReadSerializer
ProjectPostSerializer = ProjectPostReadSerializer
ProjectListSerializer = ProjectListReadSerializer
ProjectDetailSerializer = ProjectDetailReadSerializer
ContactMessageSerializer = ContactMessageWriteSerializer
