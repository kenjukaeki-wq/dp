from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from notifications.services import after_commit, notify_group
from .access import require_access, require_teacher
from .models import (
    Lesson,
    StudentLessonSession,
    ChatMessage,
    RaisedHand,
    Poll,
    PollOption,
    PollVote,
)


@transaction.atomic
def change_lesson_status(user, lesson_id, action):
    lesson = (
        Lesson.objects.select_related("group").get(pk=lesson_id)
    )
    require_teacher(user, lesson.group)
    now = timezone.now()

    if action == "start":
        if lesson.status != Lesson.Status.SCHEDULED:
            raise ValidationError("Можно начать только запланированное занятие.")
        lesson.status = Lesson.Status.LIVE
        lesson.started_at = now
        notify_group(
            lesson.group,
            f"Занятие началось: {lesson.title}",
            f"/lessons/{lesson.pk}/",
            f"lesson:{lesson.pk}:start",
        )

    elif action == "finish":
        if lesson.status != Lesson.Status.LIVE:
            raise ValidationError("Завершить можно только активное занятие.")
        lesson.status = Lesson.Status.FINISHED
        lesson.finished_at = now
        lesson.polls.filter(is_active=True).update(is_active=False)
        lesson.hands.all().delete()

        for session in lesson.sessions.filter(left_at__isnull=True):
            session.left_at = min(now, session.last_activity)
            session.save(update_fields=["left_at"])

    elif action == "cancel":
        if lesson.status != Lesson.Status.SCHEDULED:
            raise ValidationError("Отменить можно только запланированное занятие.")
        lesson.status = Lesson.Status.CANCELLED

    else:
        raise ValidationError("Неизвестное действие.")

    lesson.save(update_fields=["status", "started_at", "finished_at"])
    after_commit(f"lesson_{lesson.pk}", {"event": "lesson.state_changed"})
    return lesson


def require_live_student(user, lesson):
    require_access(user, lesson.group)
    if user.is_teacher:
        raise PermissionDenied("Это действие ученика.")
    if lesson.status != Lesson.Status.LIVE:
        raise ValidationError("Занятие сейчас не активно.")


@transaction.atomic
def heartbeat(user, lesson_id, connection_id):
    lesson = (
        Lesson.objects.select_related("group").get(pk=lesson_id)
    )
    require_access(user, lesson.group)
    if user.is_teacher or lesson.status != Lesson.Status.LIVE:
        return

    now = timezone.now()
    session = StudentLessonSession.objects.filter(connection_id=connection_id).first()

    if session:
        gap = now - session.last_activity
        if session.left_at is None and gap <= timedelta(seconds=90):
            session.last_activity = now
            session.save(update_fields=["last_activity"])
            return


        if session.left_at is None:
            session.left_at = session.last_activity
        session.connection_id = f"closed-{session.pk}-{connection_id}"[:255]
        session.save(update_fields=["left_at", "connection_id"])

    StudentLessonSession.objects.create(
        student=user,
        lesson=lesson,
        connection_id=connection_id,
        joined_at=now,
        last_activity=now,
    )


def close_session(connection_id):
    session = StudentLessonSession.objects.filter(
        connection_id=connection_id,
        left_at__isnull=True,
    ).first()
    if session:
        session.left_at = session.last_activity
        session.save(update_fields=["left_at"])


@transaction.atomic
def chat(user, lesson_id, text):
    lesson = (
        Lesson.objects.select_related("group").get(pk=lesson_id)
    )
    require_access(user, lesson.group)
    if lesson.status != Lesson.Status.LIVE:
        raise ValidationError("Чат доступен во время занятия.")
    if not isinstance(text, str) or not text.strip() or len(text) > 2000:
        raise ValidationError("Сообщение должно содержать от 1 до 2000 символов.")

    recent_messages = ChatMessage.objects.filter(
        author=user,
        lesson=lesson,
        created_at__gt=timezone.now() - timedelta(seconds=1),
    )
    if recent_messages.exists():
        raise ValidationError("Отправляйте не чаще одного сообщения в секунду.")

    message = ChatMessage.objects.create(lesson=lesson, author=user, text=text.strip())
    after_commit(
        f"lesson_{lesson.pk}",
        {
            "event": "chat.message",
            "id": message.pk,
            "author": user.display_name,
            "text": message.text,
            "time": message.created_at.isoformat(),
        },
    )


@transaction.atomic
def set_hand(user, lesson_id, raised):
    lesson = (
        Lesson.objects.select_related("group").get(pk=lesson_id)
    )
    require_live_student(user, lesson)
    if not isinstance(raised, bool):
        raise ValidationError("Некорректное состояние руки.")

    if raised:
        RaisedHand.objects.get_or_create(student=user, lesson=lesson)
    else:
        RaisedHand.objects.filter(student=user, lesson=lesson).delete()
    after_commit(f"lesson_{lesson.pk}", {"event": "hand.updated"})


@transaction.atomic
def create_poll(user, lesson_id, question, options):
    lesson = (
        Lesson.objects.select_related("group").get(pk=lesson_id)
    )
    require_teacher(user, lesson.group)
    if lesson.status != Lesson.Status.LIVE:
        raise ValidationError("Запустите занятие перед опросом.")

    if not question.strip() or len(question) > 300:
        raise ValidationError("Вопрос должен содержать от 1 до 300 символов.")
    if not 2 <= len(options) <= 6:
        raise ValidationError("Нужно от 2 до 6 вариантов.")
    if len(set(options)) != len(options):
        raise ValidationError("Варианты не должны повторяться.")
    for option in options:
        if not option.strip() or len(option) > 200:
            raise ValidationError("Вариант должен содержать от 1 до 200 символов.")
    if lesson.polls.filter(is_active=True).exists():
        raise ValidationError("Сначала завершите текущий опрос.")

    poll = Poll.objects.create(lesson=lesson, question=question.strip())
    for text in options:
        PollOption.objects.create(poll=poll, text=text.strip())
    after_commit(f"lesson_{lesson.pk}", {"event": "poll.started"})
    return poll


@transaction.atomic
def close_poll(user, lesson_id, poll_id):
    lesson = (
        Lesson.objects.select_related("group").get(pk=lesson_id)
    )
    require_teacher(user, lesson.group)
    lesson.polls.filter(pk=poll_id).update(is_active=False)
    after_commit(f"lesson_{lesson.pk}", {"event": "poll.closed"})


@transaction.atomic
def vote(user, lesson_id, poll_id, option_id):
    lesson = (
        Lesson.objects.select_related("group").get(pk=lesson_id)
    )
    require_live_student(user, lesson)
    option = PollOption.objects.filter(
        pk=option_id,
        poll_id=poll_id,
        poll__lesson=lesson,
        poll__is_active=True,
    ).first()
    if not option:
        raise ValidationError("Опрос закрыт или выбран неверный вариант.")

    answer, created = PollVote.objects.get_or_create(
        poll_id=poll_id,
        student=user,
        defaults={"option": option},
    )
    if not created:
        raise ValidationError("Вы уже ответили на этот опрос.")
    after_commit(f"lesson_{lesson.pk}_teacher", {"event": "poll.results_updated"})


def lesson_state(user, lesson_id):
    lesson = Lesson.objects.select_related("group").get(pk=lesson_id)
    require_access(user, lesson.group)
    teacher = lesson.group.teacher_id == user.pk

    polls = []
    for poll in lesson.polls.order_by("-pk")[:10]:
        options = []

        for option in poll.options.annotate(total=Count("votes")).order_by("pk"):
            option_data = {"id": option.pk, "text": option.text}
            if teacher:
                option_data["count"] = option.total
            options.append(option_data)

        polls.append(
            {
                "id": poll.pk,
                "question": poll.question,
                "active": poll.is_active,
                "voted": poll.votes.filter(student=user).exists(),
                "options": options,
            }
        )

    hands = []
    for hand in lesson.hands.select_related("student").order_by("raised_at"):
        hands.append({"id": hand.student_id, "name": hand.student.display_name})

    online_ids = []
    if lesson.status == Lesson.Status.LIVE:
        active_sessions = lesson.sessions.filter(
            left_at__isnull=True,
            last_activity__gte=timezone.now() - timedelta(seconds=90),
        )
        online_ids = list(
            active_sessions.values_list("student_id", flat=True).distinct()
        )

    messages = []
    recent_messages = list(
        lesson.chat_messages.select_related("author").order_by("-pk")[:100]
    )
    for message in reversed(recent_messages):
        messages.append(
            {
                "id": message.pk,
                "author": message.author.display_name,
                "text": message.text,
                "time": message.created_at.isoformat(),
            }
        )

    return {
        "event": "state",
        "status": lesson.status,
        "teacher": teacher,
        "hands": hands,
        "online_ids": online_ids,
        "messages": messages,
        "polls": polls,
    }


def merge_intervals(intervals):
    result = []
    for start, end in sorted(intervals):
        if not result or start > result[-1][1]:
            result.append([start, end])
        else:
            result[-1][1] = max(result[-1][1], end)
    return result


def attendance_report(lesson):
    by_student = {}
    for session in lesson.sessions.all():
        start = max(session.joined_at, lesson.started_at or session.joined_at)
        end = min(
            session.left_at or session.last_activity,
            lesson.finished_at or timezone.now(),
        )
        if end < start:
            continue
        if session.student_id not in by_student:
            by_student[session.student_id] = []
        by_student[session.student_id].append((start, end))

    rows = []
    for membership in lesson.group.memberships.select_related("student"):
        intervals = by_student.get(membership.student_id, [])
        merged = merge_intervals(intervals)
        seconds = 0
        for start, end in merged:
            seconds += (end - start).total_seconds()

        rows.append(
            {
                "student": membership.student,
                "present": bool(merged),
                "first": merged[0][0] if merged else None,
                "last": merged[-1][1] if merged else None,
                "minutes": round(seconds / 60, 1),
            }
        )
    return rows
