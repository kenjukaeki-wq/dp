from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from .forms import RegisterForm, ProfileForm
from .models import TelegramLink, TelegramToken
from .services import create_telegram_token


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("dashboard")
    return render(request, "form.html", {"form": form, "title": "Создать аккаунт"})


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Профиль сохранён.")
        return redirect("profile")
    return render(
        request,
        "accounts/profile.html",
        {
            "form": form,
            "linked": TelegramLink.objects.filter(user=request.user).exists(),
            "bot_enabled": bool(
                settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_BOT_USERNAME
            ),
        },
    )


@login_required
@require_POST
def telegram_connect(request):
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_BOT_USERNAME:
        messages.error(request, "Бот ещё не настроен в .env.")
        return redirect("profile")
    token = create_telegram_token(request.user)
    return render(
        request,
        "accounts/telegram.html",
        {
            "link": f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start={token}",
        },
    )


@login_required
@require_POST
def telegram_disconnect(request):
    TelegramLink.objects.filter(user=request.user).delete()
    TelegramToken.objects.filter(user=request.user).delete()
    messages.success(request, "Telegram отключён.")
    return redirect("profile")
