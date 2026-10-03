from rest_framework import serializers
from .models import ContactMessage, Post, Project, ProjectPost

class PostSerializer(serializers.ModelSerializer):
    # Category객체 대신에 카테고리 이름을 출력한다
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


class ProjectPostSerializer(serializers.ModelSerializer):
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


class ProjectListSerializer(serializers.ModelSerializer):
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

    def get_tags(self, obj):
        return list(
            obj.posts.filter(is_public=True)
            .values_list("tags__name", flat=True)
            .exclude(tags__name__isnull=True)
            .distinct()
            .order_by("tags__name")
        )


class ProjectDetailSerializer(ProjectListSerializer):
    posts = ProjectPostSerializer(many=True, read_only=True)

    class Meta(ProjectListSerializer.Meta):
        fields = [*ProjectListSerializer.Meta.fields, "posts"]


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["id", "name", "email", "message", "created_at"]
        read_only_fields = ["id", "created_at"]
        
