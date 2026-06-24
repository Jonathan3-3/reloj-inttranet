from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('', lambda r: redirect('dashboard' if r.user.is_authenticated else 'login')),
    path('admin/', admin.site.urls),
    path('cuentas/', include('apps.cuentas.urls')),
    path('panel/', include('apps.panel.urls')),
    path('empleados/', include('apps.empleados.urls')),
    path('horarios/', include('apps.horarios.urls')),
    path('asistencia/', include('apps.asistencia.urls')),
    path('incidencias/', include('apps.incidencias.urls')),
    path('dispositivos/', include('apps.dispositivos.urls')),
    path('registro/', include('apps.registro.urls')),
    path('reportes/', include('apps.reportes.urls')),
    path('solicitudes/', include('apps.solicitudes.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
