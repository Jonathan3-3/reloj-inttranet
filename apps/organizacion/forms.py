from django import forms
from .models import Area, Departamento

class AreaForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = ['nombre', 'responsable']

class DepartamentoForm(forms.ModelForm):
    class Meta:
        model = Departamento
        fields = ['nombre', 'area']
