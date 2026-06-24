from datetime import date
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from .models import PlantillaReporte
from apps.asistencia.models import AsistenciaDiaria


@login_required
def lista_reportes(request):
    return render(request, 'reportes/lista.html')


@login_required
@staff_member_required
def generar_reporte(request):
    tipo = request.GET.get('tipo', 'diario')
    formato = request.GET.get('formato', 'xlsx')
    desde = request.GET.get('desde', str(date.today()))
    hasta = request.GET.get('hasta', str(date.today()))

    if formato == 'xlsx':
        return _exportar_excel(tipo, desde, hasta)
    elif formato == 'csv':
        return _exportar_csv(tipo, desde, hasta)
    elif formato == 'pdf':
        return _exportar_pdf(tipo, desde, hasta)

    messages.error(request, 'Formato no soportado')
    return redirect('lista-reportes')


@login_required
def lista_plantillas(request):
    plantillas = PlantillaReporte.objects.all()
    return render(request, 'reportes/plantillas.html', {
        'plantillas': plantillas,
    })


def _exportar_excel(tipo, desde, hasta):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    qs = _obtener_datos(tipo, desde, hasta)
    wb = Workbook()
    ws = wb.active
    ws.title = 'Reporte'

    headers = ['ID', 'Nombre', 'Departamento', 'Fecha', 'Entrada',
               'Comida Inicio', 'Comida Fin', 'Salida', 'Horas',
               'Retardo (min)', 'Incidencia', 'Estatus']

    header_font = Font(bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='2C3E50', end_color='2C3E50', fill_type='solid')

    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')

    for i, a in enumerate(qs, 2):
        ws.cell(row=i, column=1, value=a.empleado.id_original)
        ws.cell(row=i, column=2, value=a.empleado.nombre)
        ws.cell(row=i, column=3, value=str(a.empleado.departamento or ''))
        ws.cell(row=i, column=4, value=a.fecha.isoformat())
        ws.cell(row=i, column=5, value=str(a.entrada or ''))
        ws.cell(row=i, column=6, value=str(a.comida_inicio or ''))
        ws.cell(row=i, column=7, value=str(a.comida_fin or ''))
        ws.cell(row=i, column=8, value=str(a.salida or ''))
        ws.cell(row=i, column=9, value=float(a.horas_jornada))
        ws.cell(row=i, column=10, value=a.minutos_retardo)
        ws.cell(row=i, column=11, value=a.incidencia_codigo)
        ws.cell(row=i, column=12, value=a.estatus)

    for col in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 18

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=reporte_{tipo}_{date.today()}.xlsx'
    wb.save(response)
    return response


def _exportar_csv(tipo, desde, hasta):
    import csv
    import io

    qs = _obtener_datos(tipo, desde, hasta)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['ID', 'Nombre', 'Departamento', 'Fecha', 'Entrada',
                     'Comida Inicio', 'Comida Fin', 'Salida', 'Horas',
                     'Retardo (min)', 'Incidencia', 'Estatus'])

    for a in qs:
        writer.writerow([
            a.empleado.id_original, a.empleado.nombre,
            str(a.empleado.departamento or ''), a.fecha.isoformat(),
            str(a.entrada or ''), str(a.comida_inicio or ''),
            str(a.comida_fin or ''), str(a.salida or ''),
            float(a.horas_jornada), a.minutos_retardo,
            a.incidencia_codigo, a.estatus,
        ])

    response = HttpResponse(buffer.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename=reporte_{tipo}_{date.today()}.csv'
    return response


def _exportar_pdf(tipo, desde, hasta):
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    import io

    qs = _obtener_datos(tipo, desde, hasta)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    elements = []

    styles = getSampleStyleSheet()
    elements.append(Paragraph(f'Reporte de {tipo}', styles['Title']))

    data = [['ID', 'Nombre', 'Depto', 'Fecha', 'Entrada', 'Salida', 'Horas', 'Retardo', 'Incidencia']]
    for a in qs:
        data.append([
            a.empleado.id_original,
            a.empleado.nombre[:20],
            str(a.empleado.departamento or '')[:15],
            a.fecha.isoformat(),
            str(a.entrada or ''),
            str(a.salida or ''),
            f'{float(a.horas_jornada):.2f}',
            str(a.minutos_retardo),
            a.incidencia_codigo or '-',
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(table)
    doc.build(elements)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=reporte_{tipo}_{date.today()}.pdf'
    return response


def _obtener_datos(tipo, desde, hasta):
    qs = AsistenciaDiaria.objects.select_related('empleado__departamento')

    if desde:
        qs = qs.filter(fecha__gte=desde)
    if hasta:
        qs = qs.filter(fecha__lte=hasta)

    if tipo == 'retardos':
        qs = qs.filter(minutos_retardo__gt=0)
    elif tipo == 'incidencias':
        qs = qs.exclude(incidencia_codigo='')
    elif tipo == 'ausentes':
        qs = qs.filter(estatus='ausente')

    return qs.order_by('empleado__nombre', 'fecha')
