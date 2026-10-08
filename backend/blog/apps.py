from django.apps import AppConfig


class BlogConfig(AppConfig):
    name = 'blog'

    def ready(self):
        # SmartBase에는 AUTO 선택지를 숨기는 공개 설정이 없어 모델 선택지를 제한합니다.
        from django_smartbase_admin.models import ColorScheme
        from django_smartbase_admin.views.user_config_view import ColorSchemeForm

        ColorSchemeForm.base_fields['color_scheme'].choices = [
            (ColorScheme.LIGHT.value, ColorScheme.LIGHT.label),
            (ColorScheme.DARK.value, ColorScheme.DARK.label),
        ]

        from . import signals  # noqa: F401
