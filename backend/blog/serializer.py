from rest_framework import serializers
from .models import Post

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
        
