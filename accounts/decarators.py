from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from functools import wraps
from django.contrib import messages

def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapped_view(request, *args, **kwargs):
        if request.user.is_staff or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        messages.error(request, "Only admins can access this page.")
        return redirect('home')
    return wrapped_view