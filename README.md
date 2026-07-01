# Reloj-Intranet

Sistema de control de asistencia para intranet empresarial.
Sustituto mejorado de BioTime Cloud con cálculo automático de retardos, ausencias e incidencias.
Integración con escáner ZKTeco SpeedFace-V3L vía Push T&A (protocolo iclock).

## Requisitos

- Python 3.14+
- Django 6.0+
- SQLite (desarrollo) / MySQL (producción)

## Instalación Rápida

```bash
cd reloj-intra
python manage.py migrate
python manage.py seed_data
python manage.py runserver 0.0.0.0:8000
```

**Credenciales de desarrollo (seed_data):**
- `admin` / `admin123` (Super Administrador)
- `rh` / `rh123` (Administrador)

**Login:** http://localhost:8000/cuentas/login/

## Estructura del Proyecto

```
reloj-intra/
├── config/
│   ├── settings/
│   │   ├── base.py       # Configuración base
│   │   └── local.py      # Desarrollo local (SQLite, DEBUG=True, ngrok CSRF)
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── cuentas/          # Usuarios, roles, autenticación
│   ├── organizacion/     # Áreas y departamentos
│   ├── empleados/        # CRUD, importación masiva, recontratación
│   ├── horarios/         # Horarios, turnos, descansos, asignación masiva
│   ├── asistencia/       # Motor de cálculo de asistencia + marcaciones
│   ├── incidencias/      # Incidencias automáticas y manuales
│   ├── dispositivos/     # Escáner ZKTeco, push T&A (iclock)
│   ├── registro/         # Check-in web con geolocalización
│   ├── reportes/         # Reportes Excel, CSV, PDF
│   ├── panel/            # Dashboard con estadísticas
│   └── solicitudes/      # Solicitudes con flujo de aprobación
├── templates/            # Plantillas HTML (sidebar, roles, notificaciones)
├── static/               # CSS, JS, imágenes
└── db.sqlite3            # Base de datos de desarrollo (en git)
```

## Módulos Principales

### Dashboard
- Estadísticas en tiempo real (empleados activos, registros hoy, retardos)
- Dispositivos conectados
- Últimos registros con polling cada 5s
- Gráfica de asistencia del mes

### Empleados
- CRUD completo con áreas y departamentos
- Importación desde TSV/CSV (compatible con exportación de BioTime)
- Renuncia y recontratación
- Búsqueda por ID o nombre
- Restablecimiento de contraseña desde el detalle del empleado

### Horarios
- Ventana de entrada configurable (ej: 07:00-09:00)
- Prórroga para retardos, tolerancia para ausencias
- Ventana de comida configurable
- Asignación por área, departamento o individual
- **Asignación Masiva** — filtra por área y departamento, muestra empleados con checkboxes pre-chequeados (los que no tienen horario), selección múltiple, búsqueda por nombre/ID

### Asistencia (Motor de Cálculo Automático)
- Clasificación inteligente de marcaciones (entrada, comida, salida)
- Cálculo automático de retardos (vs horario + prórroga)
- Detección automática de ausencias (sin registro en ventana)
- Detección de exceso de comida
- Incidencias generadas automáticamente (retardo, falta)
- Recalculo automático al recibir cada nueva marcación
- Conversión de zona horaria: timestamps del scanner como UTC → America/Mexico_City

### Incidencias
- 12 tipos predefinidos con colores
- Automáticas (retardos, faltas) y manuales
- Justificación de incidencias
- Filtros por tipo, empleado, estado

### Check-in Web
- Para trabajadores de ruta (campo, home office)
- Geolocalización automática
- Detección de dispositivo (móvil/PC) y navegador

### Dispositivos
- Registro de escáneres ZKTeco SpeedFace-V3L
- Push T&A (protocolo iclock: `/iclock/cdata`, `/iclock/getrequest`)
- Panel de conexiones web activas

### Reportes
- Diario, mensual, retardos, incidencias, ausentes
- Formatos: Excel (XLSX), CSV, PDF

## Reglas de Retardo

| Condición | Resultado | Color |
|---|---|---|
| Entrada <= Inicio + Prórroga | OK | Verde |
| Entrada entre prórroga y tolerancia | Retardo | Amarillo |
| Entrada > tolerancia o sin registro | Ausencia | Rojo |

## Roles

| Rol | Acceso |
|---|---|
| `normal` | Check-in web, solicitudes, perfil |
| `admin` | Todo excepto admin de Django y cambios de rol |
| `superadmin` | Acceso completo + admin de Django |

## Acceso Remoto (ngrok)

```bash
ngrok http 8000
```

Obtienes una URL pública (`https://xxx.ngrok-free.app`) para acceder desde cualquier red.
Requiere `CSRF_TRUSTED_ORIGINS` configurado en `config/settings/local.py`.

## Integración con ZKTeco SpeedFace-V3L

- **Puerto:** 4370 (SDK, no activo)
- **Push (activo):** Scanner envía marcaciones a `/iclock/cdata`
- **Heartbeat:** Scanner consulta `/iclock/getrequest` cada ~30s
- **IP:** `10.10.0.25` / Servidor: `10.10.0.24:8000`
- **Serial:** `TDBD235000059`
- **Configuración:** Web admin del scanner en http://10.10.0.25, Communication → Push HTTP/ADMS

## Comandos Útiles

```bash
python manage.py seed_data                               # Poblar BD de ejemplo
python manage.py sincronizar_scanner --ip 10.10.0.25     # Forzar sincronización
python manage.py runserver 0.0.0.0:8000                  # Servidor de desarrollo
python manage.py createsuperuser                         # Crear admin manualmente
```

## Producción

```bash
# Cambiar a MySQL en config/settings/prod.py
# Usar Waitress como servidor
waitress-serve --port=8000 config.wsgi:application
```

## Variables de Entorno (`.env`)

```
DJANGO_SECRET_KEY=<obligatorio>
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,10.10.0.24
DISPOSITIVO_IP=10.10.0.25
DISPOSITIVO_CLAVE=8888
DISPOSITIVO_SERIAL=TDBD235000059
```

## Licencia

Uso interno.
