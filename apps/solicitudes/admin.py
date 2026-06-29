from django.contrib import admin
from .models import Solicitud, Notificacion

@admin.register(Solicitud)
class SolicitudAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'tipo', 'fecha_inicio', 'fecha_fin', 'estatus', 'creado_en')
    list_filter = ('estatus', 'tipo')
    search_fields = ('empleado__nombre', 'empleado__id_original')
    date_hierarchy = 'creado_en'
    raw_id_fields = ('empleado', 'aprobada_por')
    readonly_fields = ('creado_en', 'actualizado_en')

@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'empleado', 'tipo', 'leida', 'creado_en')
    list_filter = ('leida', 'tipo')
    search_fields = ('titulo', 'mensaje')
