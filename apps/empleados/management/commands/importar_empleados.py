import csv
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.organizacion.models import Area, Departamento
from apps.empleados.models import Empleado, Cargo


def parsear_departamento(raw):
    raw = raw.strip()
    if not raw or raw.lower() == 'departamento':
        return None, None
    for sep in [' - ', '—']:
        if sep in raw:
            parts = raw.split(sep, 1)
            return parts[0].strip(), parts[1].strip()
    if '-' in raw:
        parts = raw.split('-', 1)
        if len(parts[0]) > 2 and len(parts[1]) > 2:
            return parts[0].strip(), parts[1].strip()
    return raw, raw


class Command(BaseCommand):
    help = 'Importa empleados desde TSV generado desde el sistema HR'

    def handle(self, *args, **options):
        User = get_user_model()

        self.stdout.write('Limpiando empleados existentes...')
        Empleado.objects.all().delete()
        Asistencia = self._get_asistencia_model()
        if Asistencia:
            Asistencia.objects.all().delete()
        Cargo.objects.all().delete()
        Departamento.objects.all().delete()
        Area.objects.all().delete()

        with open('empleados.tsv', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter='\t')
            rows = list(reader)

        self.stdout.write(f'Total filas en TSV: {len(rows)}')

        deptos_creados = {}
        cargos_creados = {}
        stats = {'creados': 0, 'saltados': 0}

        area_cache = {}

        def get_o_crea_area(nombre):
            nombre = nombre.strip()
            if nombre not in area_cache:
                area_cache[nombre] = Area.objects.get_or_create(nombre=nombre)[0]
            return area_cache[nombre]

        depto_cache = {}

        def get_o_crea_depto(raw):
            raw = raw.strip()
            if not raw or raw.lower() == 'departamento':
                return None
            if raw not in depto_cache:
                area_nombre, depto_nombre = parsear_departamento(raw)
                if area_nombre and depto_nombre:
                    area = get_o_crea_area(area_nombre)
                    depto_cache[raw] = Departamento.objects.get_or_create(
                        nombre=depto_nombre, area=area
                    )[0]
                else:
                    depto_cache[raw] = None
            return depto_cache[raw]

        cargo_cache = {}

        def get_o_crea_cargo(raw_id):
            raw_id = raw_id.strip()
            if not raw_id:
                return None
            if raw_id not in cargo_cache:
                nombre = f'Cargo {raw_id}'
                cargo_cache[raw_id] = Cargo.objects.get_or_create(nombre=nombre)[0]
            return cargo_cache[raw_id]

        for row in rows:
            id_orig = row.get('ID del empleado', '').strip().upper()
            nombre = row.get('Nombre', '').strip()
            apellidos = row.get('Apellidos', '').strip()
            raw_depto = row.get('Departamento', '').strip()
            raw_cargo = row.get('ID del Cargo', '').strip()

            if not id_orig:
                stats['saltados'] += 1
                continue

            if not nombre:
                nombre = id_orig

            departamento = get_o_crea_depto(raw_depto) if raw_depto and raw_depto.lower() != 'departamento' else None
            cargo = get_o_crea_cargo(raw_cargo) if raw_cargo else None

            empleado = Empleado.objects.create(
                id_original=id_orig,
                nombre=nombre,
                apellidos=apellidos,
                departamento=departamento,
                cargo=cargo,
            )

            username = id_orig.lower()[:150]
            if User.objects.filter(username=username).exists():
                username = f'{username}_{empleado.id}'

            user = User(
                username=username,
                first_name=nombre,
                last_name=apellidos,
            )
            user.set_unusable_password()
            user.debe_cambiar_password = True
            user.save()
            empleado.user = user
            empleado.save(update_fields=['user'])

            stats['creados'] += 1

        self.stdout.write(self.style.SUCCESS(
            f'Importación completada: {stats["creados"]} creados, {stats["saltados"]} saltados'
        ))
        self.stdout.write(f'Areas: {Area.objects.count()}')
        self.stdout.write(f'Departamentos: {Departamento.objects.count()}')
        self.stdout.write(f'Cargos: {Cargo.objects.count()}')
        self.stdout.write(f'Empleados: {Empleado.objects.count()}')

    def _get_asistencia_model(self):
        try:
            from django.apps import apps
            return apps.get_model('asistencia', 'Asistencia')
        except LookupError:
            return None
