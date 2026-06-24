# Reloj-Intranet

Sistema de control de asistencia para intranet empresarial.
Sustituto mejorado de BioTime Cloud con cálculo automático de retardos, ausencias e incidencias.

## Requisitos

- Python 3.14+
- Django 6.0+
- MySQL/MariaDB (producción) o SQLite (desarrollo local)

## Instalación Rápida

```bash
cd reloj-intra
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

**Credenciales por defecto:**
- Admin: `admin` / `admin123`
- RH: `rh` / `rh123`
- empleado `Empleado1`\ `Empleado123`

## Estructura del Proyecto

```
reloj-intra/
├── config/           # Configuración de Django
│   ├── settings/
│   │   ├── base.py   # Configuración base
│   │   └── local.py  # Configuración local (SQLite)
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── accounts/      # Autenticación y roles
│   ├── company/       # Areas y departamentos
│   ├── employees/     # Empleados (CRUD, renuncias, recontratación)
│   ├── schedules/     # Horarios y asignaciones
│   ├── attendance/    # Marcaciones y cálculo de asistencia
│   ├── incidents/     # Incidencias (automáticas y manuales)
│   ├── devices/       # Dispositivos ZKTeco y conexiones web
│   ├── checkin/       # Check-in web con geolocalización
│   ├── reports/       # Generación de reportes (Excel, CSV, PDF)
│   └── dashboard/     # Dashboard con estadísticas en tiempo real
├── templates/         # Plantillas HTML
├── static/            # Archivos estáticos (CSS, JS)
└── docs/              # Documentación
```

## Módulos Principales

### 1. Dashboard
- Estadísticas en tiempo real (empleados activos, registros hoy, retardos)
- Dispositivos conectados ahora
- Últimos registros con polling cada 5s
- Gráfica de asistencia del mes

### 2. Empleados
- CRUD completo con áreas y departamentos
- Importación desde CSV
- Renuncia y recontratación
- Búsqueda por ID o nombre

### 3. Horarios
- Ventana de entrada configurable (ej: 07:00-09:00)
- Prórroga para retardos (ej: 10 min)
- Tolerancia para ausencias (ej: 60 min)
- Ventana de comida configurable
- Asignación por área, departamento o individual

### 4. Asistencia (Motor de Cálculo Automático)
- Clasificación inteligente de punches (entrada, comida, salida)
- **Cálculo automático de retardos** (vs horario + prórroga)
- **Detección automática de ausencias** (sin registro en ventana)
- **Detección de exceso de comida**
- Incidencias generadas automáticamente (llt, finj)
- Recalculo automático al recibir cada nueva marcación

### 5. Incidencias
- 12 tipos predefinidos con colores
- Automáticas (retardos, faltas) y manuales
- Justificación de incidencias
- Filtros por tipo, empleado, estado

### 6. Check-in Web
- Para trabajadores de ruta (campo, home office)
- Geolocalización automática
- Detección de dispositivo (móvil/PC) y navegador
- Ping de conexión cada 30s para tracking en tiempo real

### 7. Dispositivos
- Registro de scanners ZKTeco SpeedFace-V3L
- Sincronización vía pyzk (protocolo PULL)
- Receptor PUSH (/iclock/cdata)
- Panel de conexiones web activas

### 8. Reportes
- Diario, mensual, retardos, incidencias, ausentes
- Formatos: Excel (XLSX), CSV, PDF
- Exportación directa con datos correctos de retardos

## Reglas de Retardo

| Condición | Resultado | Color |
|---|---|---|
| Entrada <= Inicio + Prórroga | OK | 🟢 Verde |
| Entrada entre prórroga y tolerancia | Retardo (llt) | 🟡 Amarillo |
| Entrada > tolerancia o sin registro | Ausencia (finj) | 🔴 Rojo |

## Comandos Útiles

```bash
python manage.py seed_data                    # Poblar BD de ejemplo
python manage.py sincronizar_scanner          # Sincronizar con scanner ZKTeco
python manage.py sincronizar_scanner --ip 10.10.0.237
python manage.py createsuperuser              # Crear admin manualmente
python manage.py runserver                    # Iniciar servidor de desarrollo
```

## Producción

```bash
# Cambiar a MySQL en config/settings/prod.py
# Usar Waitress como servidor
waitress-serve --port=8000 config.wsgi:application
```

## Licencia

Uso interno.
