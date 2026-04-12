from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from content.dashboard import admin_dashboard, admin_root_redirect

urlpatterns = [
    path('admin/', admin.site.admin_view(admin_root_redirect), name='admin_root'),
    path('admin/dashboard/', admin.site.admin_view(admin_dashboard), name='admin_dashboard'),
    path('admin/', admin.site.urls),
    path('', include('content.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
