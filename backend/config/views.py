from django.conf import settings
from django.contrib.auth import logout
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods, require_POST


@require_http_methods(["GET"])
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "unhealthy", "database": "down"}, status=503)
    return JsonResponse({"status": "ok", "database": "up"})


@require_http_methods(["GET"])
def home_redirect(request):
    return redirect(settings.BLOG_FRONTEND_URL)


@require_http_methods(["GET", "POST"])
def admin_login_redirect(request):
    if request.user.is_authenticated and not request.user.is_staff:
        return redirect(settings.DASHBOARD_FORBIDDEN_URL)
    return redirect(settings.DASHBOARD_LOGIN_URL)


@require_POST
def admin_logout_redirect(request):
    logout(request)
    return redirect(settings.DASHBOARD_LOGIN_URL)
