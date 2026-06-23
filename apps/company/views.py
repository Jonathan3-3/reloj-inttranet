from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .models import Area, Departamento
from .forms import AreaForm, DepartamentoForm


@staff_member_required
def lista_areas(request):
    areas = Area.objects.all().select_related('responsable')
    return render(request, 'company/areas.html', {'areas': areas})


@staff_member_required
def nueva_area(request):
    if request.method == 'POST':
        form = AreaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Area creada correctamente.')
            return redirect('lista-areas')
    else:
        form = AreaForm()
    return render(request, 'company/form.html', {'form': form, 'titulo': 'Nueva Area'})


@staff_member_required
def editar_area(request, pk):
    area = get_object_or_404(Area, pk=pk)
    if request.method == 'POST':
        form = AreaForm(request.POST, instance=area)
        if form.is_valid():
            form.save()
            messages.success(request, 'Area actualizada.')
            return redirect('lista-areas')
    else:
        form = AreaForm(instance=area)
    return render(request, 'company/form.html', {'form': form, 'titulo': 'Editar Area'})


@staff_member_required
def lista_departamentos(request):
    departamentos = Departamento.objects.all().select_related('area')
    return render(request, 'company/departamentos.html', {'departamentos': departamentos})


@staff_member_required
def nuevo_departamento(request):
    if request.method == 'POST':
        form = DepartamentoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Departamento creado.')
            return redirect('lista-departamentos')
    else:
        form = DepartamentoForm()
    return render(request, 'company/form.html', {'form': form, 'titulo': 'Nuevo Departamento'})


@staff_member_required
def editar_departamento(request, pk):
    depto = get_object_or_404(Departamento, pk=pk)
    if request.method == 'POST':
        form = DepartamentoForm(request.POST, instance=depto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Departamento actualizado.')
            return redirect('lista-departamentos')
    else:
        form = DepartamentoForm(instance=depto)
    return render(request, 'company/form.html', {'form': form, 'titulo': 'Editar Departamento'})
