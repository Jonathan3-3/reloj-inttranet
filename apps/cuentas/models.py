from django.contrib.auth.models import AbstractUser
from django.db import models

class Usuario(AbstractUser):
    ROLES = [
        ('normal', 'Normal'),
        ('admin', 'Administrador'),
        ('superadmin', 'Super Administrador'),
    ]
    rol = models.CharField('Rol', max_length=20, choices=ROLES, default='normal')
    debe_cambiar_password = models.BooleanField('Debe cambiar contraseña', default=False)

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        db_table = 'usuarios'

    def __str__(self):
        return f'{self.get_full_name()} ({self.get_rol_display()})'

    def es_admin(self):
        return self.rol in ('admin', 'superadmin')

    def es_superadmin(self):
        return self.rol == 'superadmin'
