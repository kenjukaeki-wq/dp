from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from education.access import require_access, require_teacher
from notifications.services import notify, notify_group
from .models import Assignment, Submission


def announce_assignment(assignment):
    notify_group(
        assignment.group,
        f"Новое задание: {assignment.title}",
        f"/assignments/{assignment.pk}/",
        f"assignment:{assignment.pk}:new",
    )


@transaction.atomic
def submit(user, assignment_id, text, file=None, clear_file=False):

    assignment = (
        Assignment.objects
        .select_related("group")
        .get(pk=assignment_id)
    )
    require_access(user, assignment.group)
    if user.is_teacher:
        raise PermissionDenied("Сдавать работы могут ученики.")
    if timezone.now() > assignment.deadline:
        raise ValidationError("Дедлайн прошёл. Изменение ответа недоступно.")

    submission = Submission.objects.filter(assignment=assignment, student=user).first()
    if submission and submission.graded_at:
        raise ValidationError("Работа уже проверена. Изменение ответа недоступно.")
    if not submission:
        submission = Submission(assignment=assignment, student=user)

    submission.text = text
    if file:
        submission.file = file
    elif clear_file:
        submission.file = ""
    submission.submitted_at = timezone.now()
    submission.full_clean()
    submission.save()
    return submission


@transaction.atomic
def grade(user, submission_id, score, feedback):
    assignment_id = Submission.objects.values_list("assignment_id", flat=True).get(
        pk=submission_id
    )
    assignment = (
        Assignment.objects
        .select_related("group")
        .get(pk=assignment_id)
    )
    require_teacher(user, assignment.group)
    submission = (
        Submission.objects
        .select_related("student")
        .get(pk=submission_id)
    )

    if not 0 <= score <= assignment.max_score:
        raise ValidationError("Оценка вне допустимого диапазона.")

    submission.score = score
    submission.feedback = feedback
    submission.graded_at = timezone.now()
    submission.revision += 1
    submission.full_clean()
    submission.save()


    notify(
        submission.student,
        f"Работа «{assignment.title}» проверена. Оценка: {score}/{assignment.max_score}.",
        f"/assignments/{assignment.pk}/",
        f"grade:{submission.pk}:{submission.revision}",
    )
    return submission
