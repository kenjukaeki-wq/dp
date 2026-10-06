from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from education.models import StudyGroup, Lesson, private_upload, validate_file


class Assignment(models.Model):
    group = models.ForeignKey(
        StudyGroup, on_delete=models.CASCADE, related_name="assignments"
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignments",
    )
    title = models.CharField("Название", max_length=200)
    description = models.TextField("Описание")
    deadline = models.DateTimeField("Дедлайн")
    max_score = models.PositiveIntegerField(
        "Максимальный балл",
        default=100,
        validators=[MinValueValidator(1), MaxValueValidator(10000)],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["deadline"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(max_score__gte=1, max_score__lte=10000),
                name="valid_max_score",
            )
        ]

    def clean(self):
        if self.lesson_id and self.lesson.group_id != self.group_id:
            raise ValidationError("Занятие должно принадлежать этой группе.")

    def __str__(self):
        return self.title


class AssignmentAttachment(models.Model):
    assignment = models.ForeignKey(
        Assignment, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(
        "Файл", upload_to=private_upload, validators=[validate_file]
    )


class Submission(models.Model):
    assignment = models.ForeignKey(
        Assignment, on_delete=models.CASCADE, related_name="submissions"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="submissions"
    )
    text = models.TextField("Ответ", blank=True)
    file = models.FileField(
        "Файл", upload_to=private_upload, blank=True, validators=[validate_file]
    )
    submitted_at = models.DateTimeField()
    score = models.PositiveIntegerField("Оценка", null=True, blank=True)
    feedback = models.TextField("Комментарий преподавателя", blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    revision = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "student"], name="one_submission"
            )
        ]

    def clean(self):
        if not self.text.strip() and not self.file:
            raise ValidationError("Добавьте текст ответа или файл.")
        if self.score is not None and self.score > self.assignment.max_score:
            raise ValidationError({"score": "Оценка выше максимального балла."})
