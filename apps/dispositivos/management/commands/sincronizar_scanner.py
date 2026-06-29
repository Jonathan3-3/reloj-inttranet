from django.core.management.base import BaseCommand
from apps.dispositivos.models import Dispositivo
from apps.dispositivos.scanner import sincronizar_dispositivo


class Command(BaseCommand):
    help = 'Sincroniza empleados y marcaciones desde un scanner ZKTeco'

    def add_arguments(self, parser):
        parser.add_argument('--dispositivo', type=int, help='ID del dispositivo a sincronizar')
        parser.add_argument('--ip', type=str, help='Dirección IP del dispositivo')
        parser.add_argument('--serial', type=str, help='Serial del dispositivo')

    def handle(self, *args, **options):
        if options.get('dispositivo'):
            dispositivo = Dispositivo.objects.get(pk=options['dispositivo'])
        elif options.get('ip'):
            dispositivo = Dispositivo.objects.get(ip=options['ip'])
        elif options.get('serial'):
            dispositivo = Dispositivo.objects.get(serial=options['serial'])
        else:
            dispositivo = Dispositivo.objects.filter(tipo='scanner', activo=True).first()

        if not dispositivo:
            self.stderr.write(self.style.ERROR('No se encontró ningún dispositivo'))
            return

        self.stdout.write(f'Sincronizando {dispositivo.nombre} ({dispositivo.ip})...')
        try:
            resultado = sincronizar_dispositivo(dispositivo)
            self.stdout.write(self.style.SUCCESS(
                f'Sincronización exitosa: {resultado["empleados"]} empleados, '
                f'{resultado["marcaciones"]} marcaciones nuevas'
            ))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error: {e}'))
