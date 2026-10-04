import blog.models
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0005_contactmessage_receipt_sent_at"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="BlogAsset",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("file", models.FileField(upload_to=blog.models.asset_upload_path, verbose_name="파일")),
                ("original_name", models.CharField(max_length=255, verbose_name="원본 파일명")),
                ("content_type", models.CharField(max_length=100, verbose_name="MIME 유형")),
                ("size", models.PositiveBigIntegerField(verbose_name="크기")),
                ("kind", models.CharField(choices=[("image", "이미지"), ("file", "첨부파일")], max_length=10, verbose_name="종류")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="업로드일")),
                ("uploaded_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="blog_assets", to=settings.AUTH_USER_MODEL, verbose_name="업로더")),
            ],
            options={"verbose_name": "게시글 파일", "verbose_name_plural": "게시글 파일", "ordering": ["-created_at"]},
        ),
    ]
