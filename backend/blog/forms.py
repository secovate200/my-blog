from django import forms

from .content import sanitize_content
from .models import Post, ProjectPost


class EditorJSWidget(forms.Textarea):
    def __init__(self, attrs=None):
        defaults = {"class": "editorjs-source", "rows": 24}
        defaults.update(attrs or {})
        super().__init__(defaults)

    class Media:
        css = {"all": ("admin/editorjs-admin.css",)}
        js = ("admin/editorjs-admin.js",)


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
