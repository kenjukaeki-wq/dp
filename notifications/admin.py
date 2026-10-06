from django.contrib import admin
from accounts.admin import ReadOnlyAdmin
from .models import Notification, TelegramDelivery


@admin.register(Notification)
class NotificationAdmin(ReadOnlyAdmin):
    list_display = ("recipient", "text", "created_at", "read_at")


@admin.register(TelegramDelivery)
class DeliveryAdmin(ReadOnlyAdmin):
    list_display = ("id", "status", "attempts", "next_attempt_at", "last_error")
    list_filter = ("status",)
