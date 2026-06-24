from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.contrib import messages


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
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
    return render(request, 'accounts/profile.html', {
        'usuario': request.user,
        'empleado': empleado,
    })


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
    return render(request, 'accounts/cambiar_password.html')
