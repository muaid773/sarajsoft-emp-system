from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render , get_object_or_404
from .forms import LoginForm
from django.contrib.auth import login, logout
from django.contrib import messages


def login_view(request):
    if request.user.is_authenticated:
        return redirect("app:dashboard_view")

    form = LoginForm(request, data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f"مرحبًا {user.username}")
        next_url = request.GET.get("next")
        return redirect(next_url or "app:dashboard_view")

    return render(request, "login.html", {"form": form})
def logout_view(request):
    logout(request)
    return redirect("login")