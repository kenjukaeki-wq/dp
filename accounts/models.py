from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        TEACHER = "teacher", "Преподаватель"
        STUDENT = "student", "Ученик"

    role = models.CharField(
        "Роль", max_length=10, choices=Role.choices, default=Role.STUDENT
    )

    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER

    @property
    def display_name(self):
        return self.get_full_name() or self.username


class TelegramLink(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="telegram"
    )
    chat_id = models.BigIntegerField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


class TelegramToken(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
