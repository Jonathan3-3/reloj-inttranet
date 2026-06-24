from django.contrib import admin
from .models import Marcacion, AsistenciaDiaria

@admin.register(Marcacion)
class MarcacionAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'marcado_en', 'tipo', 'fuente', 'dispositivo_serial')
    list_filter = ('fuente', 'tipo', 'marcado_en')
    search_fields = ('empleado__nombre', 'empleado__id_original')
    date_hierarchy = 'marcado_en'
    raw_id_fields = ('empleado',)

@admin.register(AsistenciaDiaria)
class AsistenciaDiariaAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'fecha', 'entrada', 'salida', 'horas_jornada',
                    'minutos_retardo', 'incidencia_codigo', 'estatus')
    list_filter = ('estatus', 'fecha', 'incidencia_codigo')
    search_fields = ('empleado__nombre', 'empleado__id_original')
    date_hierarchy = 'fecha'
    raw_id_fields = ('empleado',)
