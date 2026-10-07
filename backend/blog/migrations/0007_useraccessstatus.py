from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_approved_statuses(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    UserAccessStatus = apps.get_model("blog", "UserAccessStatus")
    UserAccessStatus.objects.bulk_create(
        [
            UserAccessStatus(user_id=user_id, status="approved")
            for user_id in User.objects.values_list("pk", flat=True)
        ],
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("blog", "0006_blogasset"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserAccessStatus",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("pending", "승인 대기"), ("approved", "승인"), ("banned", "차단")], default="pending", max_length=20, verbose_name="계정 상태")),
                ("ban_reason", models.TextField(blank=True, verbose_name="차단 사유")),
                ("reviewed_at", models.DateTimeField(blank=True, null=True, verbose_name="처리일")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="가입일")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="수정일")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_access_statuses", to=settings.AUTH_USER_MODEL, verbose_name="처리 관리자")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="access_status", to=settings.AUTH_USER_MODEL, verbose_name="사용자")),
            ],
            options={
                "verbose_name": "계정 접근 상태",
                "verbose_name_plural": "계정 접근 상태",
            },
        ),
        migrations.RunPython(create_approved_statuses, migrations.RunPython.noop),
    ]
