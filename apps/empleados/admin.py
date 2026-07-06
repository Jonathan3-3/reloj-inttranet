from django.contrib import admin
from .models import Cargo, Empleado


@admin.action(description='🔁 Forzar sincronización al escáner')
def forzar_push_escanner(modeladmin, request, queryset):
    filas = queryset.update(pendiente_push=True)
    modeladmin.message_user(request, f'Se forzó el push para {filas} empleado(s). Saldrán en los próximos 30s.')


@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    actions = [forzar_push_escanner]
    list_display = ('id_original', 'nombre', 'apellidos', 'departamento', 'cargo', 'estatus', 'pendiente_push', 'tipo_empleado', 'fecha_ingreso')
    list_filter = ('estatus', 'pendiente_push', 'tipo_empleado', 'departamento__area', 'departamento', 'cargo')
    search_fields = ('id_original', 'nombre', 'apellidos', 'email')
    list_editable = ('estatus', 'pendiente_push')
    raw_id_fields = ('user',)
    fieldsets = (
        ('Identificación', {
            'fields': ('id_original', 'nombre', 'apellidos', 'departamento', 'cargo', 'tipo_empleado')
        }),
        ('Contacto', {
            'fields': ('telefono', 'email')
        }),
        ('Información Personal', {
            'fields': ('nss', 'ciudad', 'cp', 'nacionalidad', 'genero'),
            'classes': ('collapse',)
        }),
        ('Estatus', {
            'fields': ('estatus', 'fecha_ingreso', 'fecha_renuncia', 'fecha_recontratacion')
        }),
        ('Configuración Scanner', {
            'fields': ('user', 'id_en_dispositivo', 'tipo_verificacion_scanner', 'foto', 'pendiente_push'),
            'classes': ('collapse',)
        }),
    )
