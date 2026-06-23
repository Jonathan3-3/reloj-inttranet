from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def profile(request):
    empleado = getattr(request.user, 'empleado', None)
    return render(request, 'accounts/profile.html', {
        'usuario': request.user,
        'empleado': empleado,
    })
