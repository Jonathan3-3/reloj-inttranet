from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import time, date
from apps.accounts.models import Usuario
from apps.company.models import Area, Departamento
from apps.employees.models import Empleado, Cargo
from apps.schedules.models import Horario, AsignacionHorario
from apps.incidents.models import TipoIncidencia
from apps.devices.models import Dispositivo


class Command(BaseCommand):
    help = 'Puebla la base de datos con datos de ejemplo'

    def handle(self, *args, **options):
        self.stdout.write('Creando datos de ejemplo...')

        # 1. Crear usuarios
        superadmin, _ = Usuario.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@empresa.com',
                'rol': 'superadmin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        superadmin.set_password('admin123')
        superadmin.save()

        admin, _ = Usuario.objects.get_or_create(
            username='rh',
            defaults={
                'email': 'rh@empresa.com',
                'rol': 'admin',
                'is_staff': True,
            }
        )
        admin.set_password('rh123')
        admin.save()

        self.stdout.write(self.style.SUCCESS('  OK Usuarios creados (admin/admin123, rh/rh123)'))

        # 2. Crear áreas y departamentos
        areas_data = [
            ('Dirección General', None),
            ('Operaciones', None),
            ('Recursos Humanos', None),
            ('Sistemas', None),
            ('Ventas', None),
        ]

        deptos_data = {
            'Dirección General': ['Dirección'],
            'Operaciones': ['Producción', 'Logística', 'Mantenimiento'],
            'Recursos Humanos': ['Reclutamiento', 'Nóminas'],
            'Sistemas': ['Desarrollo', 'Infraestructura', 'Soporte Técnico'],
            'Ventas': ['Ventas Internas', 'Ventas Externas', 'Servicio al Cliente'],
        }

        for nombre_area, _ in areas_data:
            area, _ = Area.objects.get_or_create(nombre=nombre_area)
            if nombre_area in deptos_data:
                for depto_nombre in deptos_data[nombre_area]:
                    Departamento.objects.get_or_create(nombre=depto_nombre, area=area)

        self.stdout.write(self.style.SUCCESS('  OK Areas y departamentos creados'))

        # 3. Crear cargos
        cargos_nombres = ['Auxiliar', 'Almacenista', 'Jefe de Área', 'Supervisor', 'Coordinador', 'Gerente', 'Analista', 'Técnico', 'Operador', 'Vendedor', 'Secretario', 'Contador', 'Chofer']
        for nombre in cargos_nombres:
            Cargo.objects.get_or_create(nombre=nombre)
        self.stdout.write(self.style.SUCCESS(f'  OK {len(cargos_nombres)} cargos creados'))

        # 4. Crear tipos de incidencia
        tipos_data = [
            ('llt', 'Llegada tarde', '#FFC107', '⚠️', True, True),
            ('finj', 'Falta injustificada', '#DC3545', '❌', True, True),
            ('sta', 'Salida temprana autorizada', '#28A745', '✅', False, False),
            ('pcgs', 'Permiso con goce sueldo', '#28A745', '✅', False, False),
            ('enf', 'Enfermedad', '#FD7E14', '🤒', False, True),
            ('hosp', 'Hospitalización', '#E74C3C', '🏥', False, True),
            ('at', 'Accidente trabajo', '#DC3545', '🩹', False, True),
            ('fall', 'Fallecimiento', '#212529', '⚫', False, True),
            ('mat', 'Maternidad', '#E83E8C', '👶', False, True),
            ('pat', 'Paternidad', '#007BFF', '👶', False, True),
            ('mate', 'Matrimonio', '#F8F9FA', '💒', False, False),
            ('inc', 'Incapacidad', '#28A745', '🩺', False, True),
        ]

        for i, (codigo, nombre, color, icono, auto, justif) in enumerate(tipos_data):
            TipoIncidencia.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nombre': nombre,
                    'color': color,
                    'icono': icono,
                    'es_automatica': auto,
                    'requiere_justificacion': justif,
                    'orden': i,
                }
            )

        self.stdout.write(self.style.SUCCESS(f'  OK {len(tipos_data)} tipos de incidencia creados'))

        # 4. Crear empleados de ejemplo
        empleados_data = [
            ('AER001', 'Juan Pérez García', 'Desarrollo'),
            ('AER002', 'María López Hernández', 'Producción'),
            ('AER003', 'Carlos Martínez Rodríguez', 'Logística'),
            ('AER004', 'Ana García Morales', 'Nóminas'),
            ('AER005', 'Pedro Sánchez Vargas', 'Ventas Internas'),
            ('AER006', 'Laura Jiménez Cruz', 'Soporte Técnico'),
            ('AER007', 'Roberto Torres Díaz', 'Ventas Externas'),
            ('AER008', 'Sofía Ramírez Ortiz', 'Reclutamiento'),
            ('AER009', 'Miguel Ángel Flores', 'Desarrollo'),
            ('AER010', 'Diana Medina Chávez', 'Servicio al Cliente'),
        ]

        for id_orig, nombre, depto_nombre in empleados_data:
            depto = Departamento.objects.filter(nombre=depto_nombre).first()
            Empleado.objects.get_or_create(
                id_original=id_orig,
                defaults={
                    'nombre': nombre,
                    'departamento': depto,
                    'estatus': 'activo',
                    'fecha_ingreso': date(2024, 1, 15),
                    'id_en_dispositivo': id_orig,
                }
            )

        self.stdout.write(self.style.SUCCESS(f'  OK {len(empleados_data)} empleados creados'))

        # 5. Crear horarios
        horario_matutino, _ = Horario.objects.get_or_create(
            nombre='Matutino',
            defaults={
                'ventana_entrada_inicio': time(7, 0),
                'ventana_entrada_fin': time(9, 0),
                'prorroga_minutos': 10,
                'tolerancia_ausencia_minutos': 60,
                'comida_ventana_inicio': time(12, 0),
                'comida_ventana_fin': time(16, 0),
                'comida_duracion_minutos': 60,
                'jornada_hrs': 8,
                'tipo_asignacion': 'departamento',
                'activo': True,
            }
        )
        for d in Departamento.objects.filter(nombre__in=['Desarrollo', 'Soporte Técnico', 'Infraestructura']):
            horario_matutino.departamentos.add(d)

        horario_ventas, _ = Horario.objects.get_or_create(
            nombre='Ventas (horario corrido)',
            defaults={
                'ventana_entrada_inicio': time(8, 0),
                'ventana_entrada_fin': time(10, 0),
                'prorroga_minutos': 10,
                'tolerancia_ausencia_minutos': 60,
                'comida_ventana_inicio': time(13, 0),
                'comida_ventana_fin': time(15, 0),
                'comida_duracion_minutos': 45,
                'jornada_hrs': 8,
                'tipo_asignacion': 'departamento',
                'activo': True,
            }
        )
        for d in Departamento.objects.filter(nombre__in=['Ventas Internas', 'Ventas Externas', 'Servicio al Cliente']):
            horario_ventas.departamentos.add(d)

        self.stdout.write(self.style.SUCCESS('  OK Horarios creados'))

        # 6. Crear dispositivo de ejemplo
        Dispositivo.objects.get_or_create(
            serial='AEYU194660027',
            defaults={
                'nombre': 'Scanner Oficina Principal',
                'ip': '10.10.0.237',
                'puerto': 4370,
                'modelo': 'SpeedFace-V3L',
                'tipo': 'scanner',
                'estado': 'offline',
            }
        )

        self.stdout.write(self.style.SUCCESS('  OK Dispositivo de ejemplo creado'))

        self.stdout.write(self.style.SUCCESS('\nOK Base de datos poblada correctamente'))
        self.stdout.write(f'   Admin: admin / admin123')
        self.stdout.write(f'   RH:    rh   / rh123')
        self.stdout.write(f'   Para iniciar: python manage.py runserver')
