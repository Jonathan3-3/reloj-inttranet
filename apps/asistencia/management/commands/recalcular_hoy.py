from django.core.management.base import BaseCommand
from apps.asistencia.calculators.engine import recalcular_todos_pendientes


class Command(BaseCommand):
    help = 'Recalcula la asistencia de todos los empleados activos para hoy'

    def handle(self, *args, **options):
        total = recalcular_todos_pendientes()
        self.stdout.write(self.style.SUCCESS(f'Recalculados {total} empleados para hoy'))
