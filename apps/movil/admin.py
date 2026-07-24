from django.contrib import admin
from .models import VersionAPK

@admin.register(VersionAPK)
class VersionAPKAdmin(admin.ModelAdmin):
    list_display = ['version', 'activa', 'peso_mb', 'creado_en']
    list_editable = ['activa']
    search_fields = ['version', 'notas']
