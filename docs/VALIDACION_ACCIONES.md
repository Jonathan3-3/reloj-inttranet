# Validación de acciones — 3 de noviembre de 2026

Bloque: recálculo masivo, restablecimiento de contraseña y buscador.

- `python tests/test_actions.py`: 8 pruebas sin acceso a base de datos. Métodos, permisos, fechas, CSRF, registro sin contraseña, retorno seguro y compilación de plantillas.
- `node tests/dashboard-polling.cjs`: manejo de respuestas y consultas sin solapamiento.
- `node tests/browser-actions.cjs`: Edge headless con API ficticia; nombres con apóstrofes/HTML, resultados vacíos, errores, sesión vencida y tres acciones POST con CSRF. Sin errores JavaScript.
- El test de navegador requiere Playwright y Edge instalados. Se puede indicar el módulo mediante PLAYWRIGHT_MODULE. Carga Bootstrap 5.3.3 desde el mismo CDN de la aplicación.
- La prueba de navegador comprueba comportamiento JavaScript, no diseño visual: usa plantillas aisladas sin el CSS/base completo. No se modificaron datos reales.
- Pendiente tras despliegue: comprobar estos flujos con una sesión real del servidor.

Los cambios de Docker, integración del servidor y otros ajustes visuales locales quedan fuera de este bloque.
