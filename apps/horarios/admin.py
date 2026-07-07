from django.contrib import admin
from .models import Horario, Turno, Descanso, AsignacionHorario, ExcepcionHorario

@admin.register(Turno)
class TurnoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'entrada_inicio', 'entrada_fin', 'jornada_hrs', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre',)

@admin.register(Descanso)
class DescansoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'hora_inicio', 'hora_fin', 'duracion_minutos', 'tipo_calculo', 'activo')
    list_filter = ('activo', 'tipo_calculo')
    search_fields = ('nombre',)

@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ventana_entrada_inicio', 'ventana_entrada_fin',
                    'jornada_hrs', 'clasificacion_secuencial',
                    'tipo_asignacion', 'turno', 'descanso', 'activo')
    list_filter = ('activo', 'tipo_asignacion', 'clasificacion_secuencial')
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
