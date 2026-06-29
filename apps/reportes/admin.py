from django.contrib import admin
from .models import PlantillaReporte, ReporteGenerado

@admin.register(PlantillaReporte)
class PlantillaReporteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'formato', 'creado_en')
    list_filter = ('tipo', 'formato')

@admin.register(ReporteGenerado)
class ReporteGeneradoAdmin(admin.ModelAdmin):
    list_display = ('plantilla', 'generado_por', 'creado_en', 'descargado')
    list_filter = ('descargado', 'creado_en')
