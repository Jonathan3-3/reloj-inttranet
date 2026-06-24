import csv
import io
import secrets
import string
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.conf import settings
from .models import Empleado, Cargo
from apps.company.models import Area, Departamento
from apps.attendance.calculators.engine import recalcular_asistencia


def generar_password(longitud=10):
    caracteres = string.ascii_letters + string.digits
    return ''.join(secrets.choice(caracteres) for _ in range(longitud))


@login_required
def lista_empleados(request):
    estatus = request.GET.get('estatus', '')
    departamento = request.GET.get('departamento', '')
    q = request.GET.get('q', '')

    qs = Empleado.objects.select_related('departamento', 'cargo', 'user')

    if estatus:
        qs = qs.filter(estatus=estatus)
    if departamento:
        qs = qs.filter(departamento_id=departamento)
    if q:
        qs = qs.filter(Q(id_original__icontains=q) | Q(nombre__icontains=q) | Q(apellidos__icontains=q))

    qs = qs.order_by('nombre')

    departamentos = Departamento.objects.all().select_related('area').order_by('area__nombre', 'nombre')

    return render(request, 'employees/list.html', {
        'empleados': qs,
        'departamentos': departamentos,
        'filtro_estatus': estatus,
        'filtro_departamento': departamento,
        'filtro_q': q,
    })


@login_required
def detalle_empleado(request, pk):
    empleado = get_object_or_404(
        Empleado.objects.select_related('departamento__area', 'cargo', 'user'), pk=pk
    )
    return render(request, 'employees/detail.html', {
        'empleado': empleado,
    })


def _extraer_datos_empleado(request):
    return {
        'id_original': request.POST.get('id_original', '').strip().upper(),
        'nombre': request.POST.get('nombre', '').strip(),
        'apellidos': request.POST.get('apellidos', '').strip(),
        'departamento_id': request.POST.get('departamento'),
        'cargo_id': request.POST.get('cargo'),
        'tipo_empleado': request.POST.get('tipo_empleado', 'empleado'),
        'telefono': request.POST.get('telefono', ''),
        'email': request.POST.get('email', ''),
        'fecha_ingreso': request.POST.get('fecha_ingreso') or None,
        'nss': request.POST.get('nss', ''),
        'ciudad': request.POST.get('ciudad', ''),
        'cp': request.POST.get('cp', ''),
        'nacionalidad': request.POST.get('nacionalidad', ''),
        'genero': request.POST.get('genero', ''),
        'id_en_dispositivo': request.POST.get('id_en_dispositivo', ''),
        'tipo_verificacion_scanner': request.POST.get('tipo_verificacion_scanner', 'facial'),
        'area_id': request.POST.get('area'),
    }


@login_required
@staff_member_required
def nuevo_empleado(request):
    datos = {}
    if request.method == 'POST':
        datos = _extraer_datos_empleado(request)
        foto = request.FILES.get('foto')

        if not datos['id_original'] or not datos['nombre']:
            messages.error(request, 'ID original y nombre(s) son obligatorios.')
        elif Empleado.objects.filter(id_original=datos['id_original']).exists():
            messages.error(request, f"El ID {datos['id_original']} ya existe.")
        else:
            departamento = Departamento.objects.filter(pk=datos['departamento_id']).first() if datos['departamento_id'] else None
            cargo = Cargo.objects.filter(pk=datos['cargo_id']).first() if datos['cargo_id'] else None

            empleado = Empleado.objects.create(
                id_original=datos['id_original'],
                nombre=datos['nombre'],
                apellidos=datos['apellidos'],
                departamento=departamento,
                cargo=cargo,
                tipo_empleado=datos['tipo_empleado'],
                telefono=datos['telefono'],
                email=datos['email'],
                fecha_ingreso=datos['fecha_ingreso'],
                nss=datos['nss'],
                ciudad=datos['ciudad'],
                cp=datos['cp'],
                nacionalidad=datos['nacionalidad'],
                genero=datos['genero'],
                id_en_dispositivo=datos['id_en_dispositivo'] or datos['id_original'],
                tipo_verificacion_scanner=datos['tipo_verificacion_scanner'],
                foto=foto,
            )

            temp_password = generar_password()
            from django.contrib.auth import get_user_model
            UserModel = get_user_model()

            username = datos['id_original'].lower()
            if UserModel.objects.filter(username=username).exists():
                username = f'{username}_{empleado.id}'

            user = UserModel.objects.create_user(
                username=username,
                password=temp_password,
                email=datos['email'],
                first_name=datos['nombre'],
                last_name=datos['apellidos'],
            )
            user.rol = datos['tipo_empleado']
            user.debe_cambiar_password = True
            user.save()

            empleado.user = user
            empleado.save(update_fields=['user'])

            messages.success(
                request,
                f'Empleado {datos["nombre"]} {datos["apellidos"]} creado.<br>'
                f'<strong>Usuario:</strong> {username}<br>'
                f'<strong>Contraseña temporal:</strong> {temp_password}'
            )
            return redirect('lista-empleados')

    areas = Area.objects.all().order_by('nombre')
    cargos = Cargo.objects.all().order_by('nombre')
    departamentos = Departamento.objects.filter(area_id=datos.get('area_id')).order_by('nombre') if datos.get('area_id') else Departamento.objects.none()
    return render(request, 'employees/form.html', {
        'areas': areas,
        'cargos': cargos,
        'departamentos': departamentos,
        'val': datos,
        'titulo': 'Nuevo Empleado',
    })


@login_required
@staff_member_required
def editar_empleado(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)

    if request.method == 'POST':
        empleado.id_original = request.POST.get('id_original', empleado.id_original).strip().upper()
        empleado.nombre = request.POST.get('nombre', '').strip()
        empleado.apellidos = request.POST.get('apellidos', '').strip()
        depto_id = request.POST.get('departamento')
        empleado.departamento = Departamento.objects.filter(pk=depto_id).first() if depto_id else None
        cargo_id = request.POST.get('cargo')
        empleado.cargo = Cargo.objects.filter(pk=cargo_id).first() if cargo_id else None
        empleado.tipo_empleado = request.POST.get('tipo_empleado', 'empleado')
        empleado.telefono = request.POST.get('telefono', '')
        empleado.email = request.POST.get('email', '')
        empleado.fecha_ingreso = request.POST.get('fecha_ingreso') or None
        empleado.nss = request.POST.get('nss', '')
        empleado.ciudad = request.POST.get('ciudad', '')
        empleado.cp = request.POST.get('cp', '')
        empleado.nacionalidad = request.POST.get('nacionalidad', '')
        empleado.genero = request.POST.get('genero', '')
        empleado.id_en_dispositivo = request.POST.get('id_en_dispositivo', '')
        empleado.tipo_verificacion_scanner = request.POST.get('tipo_verificacion_scanner', 'facial')
        if request.FILES.get('foto'):
            empleado.foto = request.FILES['foto']
        empleado.save()

        # Actualizar usuario vinculado si existe
        if empleado.user:
            empleado.user.first_name = empleado.nombre
            empleado.user.last_name = empleado.apellidos
            empleado.user.email = empleado.email
            empleado.user.rol = empleado.tipo_empleado
            empleado.user.save()

        messages.success(request, 'Empleado actualizado correctamente.')
        return redirect('lista-empleados')

    areas = Area.objects.all().order_by('nombre')
    cargos = Cargo.objects.all().order_by('nombre')
    departamentos = Departamento.objects.filter(
        area=empleado.departamento.area if empleado.departamento else None
    ).order_by('nombre') if empleado.departamento else Departamento.objects.none()

    val = {
        'id_original': empleado.id_original,
        'nombre': empleado.nombre,
        'apellidos': empleado.apellidos,
        'departamento': empleado.departamento,
        'departamento_id': empleado.departamento_id,
        'cargo_id': empleado.cargo_id,
        'cargo': empleado.cargo,
        'tipo_empleado': empleado.tipo_empleado,
        'telefono': empleado.telefono,
        'email': empleado.email,
        'fecha_ingreso': empleado.fecha_ingreso.isoformat() if empleado.fecha_ingreso else '',
        'nss': empleado.nss,
        'ciudad': empleado.ciudad,
        'cp': empleado.cp,
        'nacionalidad': empleado.nacionalidad,
        'genero': empleado.genero,
        'id_en_dispositivo': empleado.id_en_dispositivo,
        'tipo_verificacion_scanner': empleado.tipo_verificacion_scanner,
        'area_id': empleado.departamento.area_id if empleado.departamento else '',
        'foto': empleado.foto,
    }
    return render(request, 'employees/form.html', {
        'empleado': empleado,
        'val': val,
        'areas': areas,
        'cargos': cargos,
        'departamentos': departamentos,
        'titulo': 'Editar Empleado',
    })


@login_required
@staff_member_required
def renuncia_empleado(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)

    if request.method == 'POST':
        fecha_renuncia = request.POST.get('fecha_renuncia') or date.today()
        empleado.estatus = 'renuncia'
        empleado.fecha_renuncia = fecha_renuncia
        empleado.save()
        messages.success(request, f'{empleado.nombre_completo} marcado como renuncia.')
        return redirect('lista-empleados')

    return render(request, 'employees/resign.html', {
        'empleado': empleado,
    })


@login_required
@staff_member_required
def recontratar_empleado(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)

    if request.method == 'POST':
        empleado.estatus = 'activo'
        empleado.fecha_recontratacion = date.today()
        empleado.fecha_renuncia = None
        empleado.save()
        messages.success(request, f'{empleado.nombre_completo} recontratado exitosamente.')
        return redirect('lista-empleados')

    return render(request, 'employees/reactivate.html', {
        'empleado': empleado,
    })


@login_required
@staff_member_required
def importar_csv(request):
    if request.method == 'POST' and request.FILES.get('archivo'):
        archivo = request.FILES['archivo']
        decoded = archivo.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded))

        creados = 0
        actualizados = 0
        errores = 0

        for row in reader:
            try:
                id_orig = row.get('id_original', '').strip().upper()
                nombre = row.get('nombre', '').strip()
                if not id_orig or not nombre:
                    errores += 1
                    continue

                _, created = Empleado.objects.update_or_create(
                    id_original=id_orig,
                    defaults={
                        'nombre': nombre,
                        'apellidos': row.get('apellidos', ''),
                        'telefono': row.get('telefono', ''),
                        'email': row.get('email', ''),
                    }
                )
                if created:
                    creados += 1
                else:
                    actualizados += 1
            except Exception:
                errores += 1

        messages.success(
            request,
            f'Importación completada: {creados} creados, {actualizados} actualizados, {errores} errores'
        )
        return redirect('lista-empleados')

    return render(request, 'employees/import.html')


def buscar_empleados_api(request):
    q = request.GET.get('q', '')
    empleados = Empleado.objects.filter(estatus='activo')
    if q:
        empleados = empleados.filter(
            Q(id_original__icontains=q) | Q(nombre__icontains=q) | Q(apellidos__icontains=q)
        )
    empleados = empleados.order_by('nombre')[:20]

    return JsonResponse({
        'empleados': [{
            'id': e.id,
            'id_original': e.id_original,
            'nombre': e.nombre_completo,
            'departamento': str(e.departamento or ''),
        } for e in empleados]
    })


def departamentos_por_area_api(request):
    area_id = request.GET.get('area_id')
    if not area_id:
        return JsonResponse({'departamentos': []})
    deptos = Departamento.objects.filter(area_id=area_id).order_by('nombre')
    return JsonResponse({
        'departamentos': [{'id': d.id, 'nombre': d.nombre} for d in deptos]
    })
