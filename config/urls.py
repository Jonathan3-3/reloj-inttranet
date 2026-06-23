from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('', lambda r: redirect('dashboard' if r.user.is_authenticated else 'login')),
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('employees/', include('apps.employees.urls')),
    path('schedules/', include('apps.schedules.urls')),
    path('attendance/', include('apps.attendance.urls')),
    path('incidents/', include('apps.incidents.urls')),
    path('devices/', include('apps.devices.urls')),
    path('checkin/', include('apps.checkin.urls')),
    path('reports/', include('apps.reports.urls')),
    path('solicitudes/', include('apps.solicitudes.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
