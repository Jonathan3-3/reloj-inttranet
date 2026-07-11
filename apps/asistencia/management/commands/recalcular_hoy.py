from datetime import date
from django.core.management.base import BaseCommand
from apps.asistencia.calculators.engine import recalcular_todos_pendientes


class Command(BaseCommand):
    help = 'Recalcula la asistencia de todos los empleados activos (rango opcional)'

    def add_arguments(self, parser):
        parser.add_argument('--desde', type=str, help='Fecha inicio YYYY-MM-DD')
        parser.add_argument('--hasta', type=str, help='Fecha fin YYYY-MM-DD')

    def handle(self, *args, **options):
        desde = date.fromisoformat(options['desde']) if options.get('desde') else None
        hasta = date.fromisoformat(options['hasta']) if options.get('hasta') else None
        total = recalcular_todos_pendientes(desde, hasta)
        rango = f'{desde or "hoy"} a {hasta or "hoy"}'
        self.stdout.write(self.style.SUCCESS(f'Recalculados {total} registros de {rango}'))
