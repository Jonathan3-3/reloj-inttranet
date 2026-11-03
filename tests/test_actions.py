import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
os.environ['DJANGO_SECRET_KEY'] = 'test-only-not-a-deployment-key'
import django
django.setup()
from django.test import RequestFactory, SimpleTestCase
from apps.asistencia.views import api_recalcular_todos
from apps.cuentas.views import restablecer_contrasena
from django.template import engines

class ActionTests(SimpleTestCase):
    def request(self, method='post', query='', staff=True):
        r=getattr(RequestFactory(), method)('/asistencia/api/recalcular/todos/'+query)
        r.user=SimpleNamespace(is_authenticated=True, is_active=True, is_staff=staff, rol='admin' if staff else 'empleado', pk=1)
        return r

    @patch('apps.asistencia.calculators.engine.recalcular_todos_pendientes')
    def test_recalculation_rejects_get_and_bad_ranges(self, engine):
        self.assertEqual(api_recalcular_todos(self.request('get')).status_code, 405)
        for query in ['?desde=incorrecta', '?hasta=2026-02-30', '?desde=2026-11-03&hasta=2026-11-01']:
            self.assertEqual(api_recalcular_todos(self.request(query=query)).status_code, 400)
        engine.assert_not_called()

    @patch('apps.asistencia.calculators.engine.recalcular_todos_pendientes', return_value=2)
    def test_recalculation_uses_validated_dates(self, engine):
        from datetime import date
        self.assertEqual(api_recalcular_todos(self.request(query='?desde=2026-11-01&hasta=2026-11-03')).status_code, 200)
        engine.assert_called_once_with(date(2026,11,1), date(2026,11,3))

    @patch('apps.asistencia.calculators.engine.recalcular_todos_pendientes')
    def test_non_staff_cannot_recalculate(self, engine):
        self.assertEqual(api_recalcular_todos(self.request(staff=False)).status_code, 302)
        engine.assert_not_called()

    @patch('django.contrib.auth.get_user_model')
    def test_reset_get_never_reads_user(self, model):
        self.assertEqual(restablecer_contrasena(self.request('get'), 2).status_code, 405)
        model.assert_not_called()

    @patch('apps.cuentas.views.messages.success')
    @patch('django.contrib.auth.get_user_model')
    def test_reset_does_not_log_password_or_redirect_offsite(self, model, message):
        user=Mock(pk=2, username='test')
        model.return_value.objects.get.return_value=user
        r=self.request()
        r.META['HTTP_REFERER']='https://external.invalid/'
        with self.assertLogs('apps.cuentas.views', level='INFO') as logs:
            response=restablecer_contrasena(r, 2)
        password=user.set_password.call_args.args[0]
        self.assertNotIn(password, '\n'.join(logs.output))
        self.assertNotIn('external.invalid', response.url)
        user.save.assert_called_once()

    def test_csrf_rejects_mutations_without_token(self):
        from django.middleware.csrf import CsrfViewMiddleware
        middleware = CsrfViewMiddleware(lambda request: None)
        for view, args in [(api_recalcular_todos, ()), (restablecer_contrasena, (2,))]:
            with self.subTest(view=view.__name__):
                response = middleware.process_view(self.request(), view, args, {})
                self.assertEqual(response.status_code, 403)

    @patch('django.contrib.auth.get_user_model')
    def test_regular_user_cannot_reset_password(self, model):
        self.assertEqual(restablecer_contrasena(self.request(staff=False), 2).status_code, 302)
        model.assert_not_called()

    def test_all_templates_compile(self):
        for p in (Path(__file__).resolve().parents[1]/'templates').rglob('*.html'):
            with self.subTest(template=p.name):
                engines['django'].from_string(p.read_text(encoding='utf-8'))

if __name__ == '__main__':
    unittest.main()
