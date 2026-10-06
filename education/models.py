import secrets
import uuid
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import models


def invitation_code():
    return "EDU-" + secrets.token_hex(5).upper()


def private_upload(instance, filename):

    return f"{instance._meta.app_label}/{uuid.uuid4().hex}{Path(filename).suffix.lower()[:12]}"


def validate_file(file):
    if file.size > 20 * 1024 * 1024:
        raise ValidationError("Максимальный размер файла — 20 МБ.")


def validate_http_url(value):
    URLValidator(schemes=["https", "http"])(value)


class StudyGroup(models.Model):
    title = models.CharField("Название", max_length=160)
    description = models.TextField("Описание", blank=True)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="teaching_groups",
    )
    invite_code = models.CharField(
        max_length=20, default=invitation_code, unique=True, editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class GroupMembership(models.Model):
    group = models.ForeignKey(
        StudyGroup, on_delete=models.CASCADE, related_name="memberships"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["group", "student"], name="unique_group_student"
            )
        ]


class Lesson(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Запланировано"
        LIVE = "live", "Идёт занятие"
        FINISHED = "finished", "Завершено"
        CANCELLED = "cancelled", "Отменено"

    group = models.ForeignKey(
        StudyGroup, on_delete=models.CASCADE, related_name="lessons"
    )
    title = models.CharField("Название", max_length=160)
    topic = models.CharField("Тема", max_length=200)
    description = models.TextField("Описание", blank=True)
    starts_at = models.DateTimeField("Начало")
    ends_at = models.DateTimeField("Окончание")
    meeting_url = models.URLField(
        "Ссылка на видеоконференцию", blank=True, validators=[validate_http_url]
    )
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.SCHEDULED
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["starts_at"]
        indexes = [models.Index(fields=["status", "starts_at"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_at__gt=models.F("starts_at")),
                name="lesson_end_after_start",
            )
        ]

    def clean(self):
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "Окончание должно быть позже начала."})

    def __str__(self):
        return self.title


class Material(models.Model):
    group = models.ForeignKey(
        StudyGroup, on_delete=models.CASCADE, related_name="materials"
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="materials",
    )
    title = models.CharField("Название", max_length=200)
    file = models.FileField(
        "Файл", upload_to=private_upload, blank=True, validators=[validate_file]
    )
    url = models.URLField("Ссылка", blank=True, validators=[validate_http_url])
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if bool(self.file) == bool(self.url):
            raise ValidationError("Прикрепите файл или укажите ссылку — одно из двух.")
        if self.lesson_id and self.lesson.group_id != self.group_id:
            raise ValidationError("Занятие должно принадлежать этой группе.")


class StudentLessonSession(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="sessions"
    )
    connection_id = models.CharField(max_length=255, unique=True)
    joined_at = models.DateTimeField()
    last_activity = models.DateTimeField()
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["lesson", "student"])]


class ChatMessage(models.Model):
    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="chat_messages"
    )
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.CharField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]


class RaisedHand(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="hands")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    raised_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["lesson", "student"], name="unique_raised_hand"
            )
        ]


class Poll(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="polls")
    question = models.CharField("Вопрос", max_length=300)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["lesson"],
                condition=models.Q(is_active=True),
                name="one_active_poll",
            )
        ]


class PollOption(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=200)


class PollVote(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="votes")
    option = models.ForeignKey(
        PollOption, on_delete=models.CASCADE, related_name="votes"
    )
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["poll", "student"], name="one_vote_per_student"
            )
        ]

    def clean(self):
        if self.option_id and self.option.poll_id != self.poll_id:
            raise ValidationError("Вариант не относится к этому опросу.")
