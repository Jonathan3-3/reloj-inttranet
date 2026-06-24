from django.contrib import admin
from .models import ConexionWeb

@admin.register(ConexionWeb)
class ConexionWebAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'tipo_dispositivo', 'ip_address', 'conectado_desde',
                    'ultimo_ping', 'activa')
    list_filter = ('activa', 'tipo_dispositivo')
    search_fields = ('empleado__nombre', 'ip_address')
