from django.contrib import admin
from .models import Horario, AsignacionHorario, ExcepcionHorario

@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ventana_entrada_inicio', 'ventana_entrada_fin',
                    'prorroga_minutos', 'tipo_asignacion', 'activo')
    list_filter = ('activo', 'tipo_asignacion')
    search_fields = ('nombre',)

@admin.register(AsignacionHorario)
class AsignacionHorarioAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'horario', 'fecha_inicio', 'fecha_fin')
    list_filter = ('horario', 'fecha_inicio')
    search_fields = ('empleado__nombre',)

@admin.register(ExcepcionHorario)
class ExcepcionHorarioAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'fecha', 'entrada_esperada', 'salida_esperada', 'motivo')
    list_filter = ('fecha',)
    search_fields = ('empleado__nombre', 'motivo')
