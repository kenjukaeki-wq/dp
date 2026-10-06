from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Notification


@login_required
def inbox(request):
    page = Paginator(request.user.notifications.all(), 30).get_page(
        request.GET.get("page")
    )
    return render(request, "notifications/inbox.html", {"page": page})


@login_required
@require_POST
def read(request, pk):
    item = get_object_or_404(Notification, pk=pk, recipient=request.user)
    item.read_at = timezone.now()
    item.save(update_fields=["read_at"])
    return redirect(item.url)


@login_required
@require_POST
def read_all(request):
    request.user.notifications.filter(read_at__isnull=True).update(
        read_at=timezone.now()
    )
    return redirect("notifications")
