from django.contrib import admin
from .models import Dispositivo

@admin.register(Dispositivo)
class DispositivoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'serial', 'ip', 'tipo', 'modelo', 'estado', 'ultimo_ping')
    list_filter = ('tipo', 'estado', 'modelo')
    search_fields = ('nombre', 'serial', 'ip')
