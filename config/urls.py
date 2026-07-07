from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from apps.registro import views as registro_views

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
    path('iclock/getrequest', registro_views.iclock_getrequest),
    path('iclock/cdata', registro_views.iclock_cdata),
    path('iclock/device', registro_views.iclock_device),
    path('reportes/', include('apps.reportes.urls')),
    path('organizacion/', include('apps.organizacion.urls')),
    path('solicitudes/', include('apps.solicitudes.urls')),
    path('api/', include('apps.api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
