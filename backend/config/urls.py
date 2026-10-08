"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import include, path
from django_smartbase_admin.admin.site import sb_admin_site
from .views import admin_login_redirect, admin_logout_redirect

urlpatterns = [
    path('admin/login/', admin_login_redirect, name='dashboard-admin-login'),
    path('admin/logout/', admin_logout_redirect, name='dashboard-admin-logout'),
    path('admin/', sb_admin_site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('blog/', include('blog.urls')),
]
