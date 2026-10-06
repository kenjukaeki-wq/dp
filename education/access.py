from django.core.exceptions import PermissionDenied
from django.db.models import Q
from .models import StudyGroup


def groups_for(user):
    return StudyGroup.objects.filter(
        Q(teacher=user) | Q(memberships__student=user)
    ).distinct()


def can_access(user, group):
    return user.is_authenticated and (
        group.teacher_id == user.pk or group.memberships.filter(student=user).exists()
    )


def require_access(user, group):
    if not can_access(user, group):
        raise PermissionDenied("Нет доступа к этой группе.")


def require_teacher(user, group=None):
    if (
        not user.is_authenticated
        or not user.is_teacher
        or (group and group.teacher_id != user.pk)
    ):
        raise PermissionDenied("Действие доступно только преподавателю этой группы.")
