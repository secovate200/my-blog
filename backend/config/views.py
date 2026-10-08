from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods, require_POST


@require_http_methods(["GET", "POST"])
def admin_login_redirect(request):
    if request.user.is_authenticated and not request.user.is_staff:
        return redirect(settings.DASHBOARD_FORBIDDEN_URL)
    return redirect(settings.DASHBOARD_LOGIN_URL)


@require_POST
def admin_logout_redirect(request):
    logout(request)
    return redirect(settings.DASHBOARD_LOGIN_URL)
