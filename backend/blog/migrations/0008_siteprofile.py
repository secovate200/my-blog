from django.db import migrations, models
import django.core.validators


def create_default_profile(apps, schema_editor):
    SiteProfile = apps.get_model("blog", "SiteProfile")
    SiteProfile.objects.create(
        id=1,
        name="SECOVATE200",
        role="BUG HUNTER",
        bio="보안 취약점과 개발 과정에서 배운 내용을 기록합니다.",
    )


class Migration(migrations.Migration):
    dependencies = [("blog", "0007_useraccessstatus")]
    operations = [
        migrations.CreateModel(
            name="SiteProfile",
            fields=[
                ("id", models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(default="SECOVATE200", max_length=100, verbose_name="이름")),
                ("role", models.CharField(blank=True, default="BUG HUNTER", max_length=100, verbose_name="역할")),
                ("bio", models.TextField(blank=True, max_length=500, verbose_name="소개")),
                ("logo", models.FileField(blank=True, help_text="PNG, JPG, WEBP 또는 GIF 이미지를 업로드하세요.", upload_to="profile/", validators=[django.core.validators.FileExtensionValidator(["png", "jpg", "jpeg", "webp", "gif"])], verbose_name="로고")),
                ("instagram_url", models.URLField(blank=True, verbose_name="Instagram URL")),
                ("github_url", models.URLField(blank=True, verbose_name="GitHub URL")),
                ("facebook_url", models.URLField(blank=True, verbose_name="Facebook URL")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="수정일")),
            ],
            options={"verbose_name": "블로그 프로필", "verbose_name_plural": "블로그 프로필"},
        ),
        migrations.RunPython(create_default_profile, migrations.RunPython.noop),
    ]
