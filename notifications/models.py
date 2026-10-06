from django.conf import settings
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    text = models.CharField(max_length=500)
    url = models.CharField(max_length=250)
    event_key = models.CharField(max_length=180)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["recipient", "event_key"], name="unique_recipient_event"
            )
        ]


class TelegramDelivery(models.Model):
    notification = models.OneToOneField(Notification, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=12,
        default="pending",
        choices=[
            ("pending", "Ожидает"),
            ("sending", "Отправляется"),
            ("sent", "Отправлено"),
            ("failed", "Ошибка"),
            ("skipped", "Пропущено"),
        ],
    )
    attempts = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    locked_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=300, blank=True)

    class Meta:
        indexes = [models.Index(fields=["status", "next_attempt_at"])]
