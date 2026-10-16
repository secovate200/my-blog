"""관리자 입력을 모델 저장 전에 검증하고 사용하기 좋은 형태로 정리합니다."""

from django import forms

from .content import sanitize_content
from .models import Post, ProjectPost, SiteProfile


class SiteProfileAdminForm(forms.ModelForm):
    """단일 프로필 설정에 맞춘 간결한 관리자 입력 폼입니다."""

    logo = forms.FileField(
        label="새 로고 업로드",
        required=False,
        widget=forms.FileInput(attrs={"accept": "image/png,image/jpeg,image/webp,image/gif"}),
        help_text="기존 로고를 바꾸려면 새 이미지를 선택하세요. PNG, JPG, WEBP, GIF를 지원합니다.",
    )
    class Meta:
        model = SiteProfile
        fields = [
            "name", "role", "bio", "logo",
            "instagram_url", "github_url", "facebook_url",
        ]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4}),
            "instagram_url": forms.URLInput(attrs={"placeholder": "https://instagram.com/..."}),
            "github_url": forms.URLInput(attrs={"placeholder": "https://github.com/..."}),
            "facebook_url": forms.URLInput(attrs={"placeholder": "https://facebook.com/..."}),
        }



class EditorJSWidget(forms.Textarea):
    def __init__(self, attrs=None):
        defaults = {"class": "editorjs-source", "rows": 24}
        defaults.update(attrs or {})
        super().__init__(defaults)

    class Media:
        css = {"all": ("admin/editorjs-admin.css",)}
        js = ("admin/editorjs-admin-v3.js",)


class RichContentAdminForm(forms.ModelForm):
    content = forms.CharField(label="본문", widget=EditorJSWidget)

    def clean_content(self):
        return sanitize_content(self.cleaned_data["content"])


class PostAdminForm(RichContentAdminForm):
    class Meta:
        model = Post
        fields = "__all__"


class ProjectPostAdminForm(RichContentAdminForm):
    class Meta:
        model = ProjectPost
        fields = "__all__"
