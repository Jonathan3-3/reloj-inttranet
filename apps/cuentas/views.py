from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.contrib import messages


class CustomLoginView(LoginView):
    template_name = 'cuentas/iniciar_sesion.html'
    redirect_authenticated_user = True
    next_page = 'dashboard'

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        if user.debe_cambiar_password:
            return redirect('cambiar-password')
        return redirect(self.get_redirect_url() or 'dashboard')


@login_required
def profile(request):
    empleado = getattr(request.user, 'empleado', None)
    return render(request, 'cuentas/perfil.html', {
        'usuario': request.user,
        'empleado': empleado,
    })


@login_required
@user_passes_test(lambda u: u.rol in ('admin', 'superadmin'))
def restablecer_contrasena(request, user_id):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
        import secrets
        import string
        new_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
        user.set_password(new_password)
        user.debe_cambiar_password = True
        user.save()
        full_name = user.get_full_name() or user.username
        messages.success(
            request,
            f'Contraseña restablecida para {full_name}.\n'
            f'Usuario: {user.username}\n'
            f'Nueva contraseña: {new_password}'
        )
    except User.DoesNotExist:
        messages.error(request, 'Usuario no encontrado.')
    return redirect(request.META.get('HTTP_REFERER', 'lista-empleados'))


@login_required
def cambiar_password(request):
    if request.method == 'POST':
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        if not password1 or len(password1) < 6:
            messages.error(request, 'La contraseña debe tener al menos 6 caracteres.')
        elif password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
        else:
            request.user.set_password(password1)
            request.user.debe_cambiar_password = False
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Contraseña cambiada exitosamente.')
            return redirect('dashboard')
    return render(request, 'cuentas/cambiar_password.html')
