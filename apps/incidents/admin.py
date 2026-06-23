from django.contrib import admin
from .models import TipoIncidencia, RegistroIncidencia

@admin.register(TipoIncidencia)
class TipoIncidenciaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'color', 'es_automatica', 'requiere_justificacion')
    list_filter = ('es_automatica',)

@admin.register(RegistroIncidencia)
class RegistroIncidenciaAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'tipo', 'fecha', 'minutos', 'justificada', 'atendida_por')
    list_filter = ('justificada', 'tipo', 'fecha')
    search_fields = ('empleado__nombre', 'empleado__id_original')
    date_hierarchy = 'fecha'
