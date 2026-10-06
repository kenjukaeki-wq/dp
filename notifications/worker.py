from datetime import timedelta

from asgiref.sync import sync_to_async
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import TelegramLink
from education.models import Lesson, StudentLessonSession
from assignments.models import Assignment
from .models import TelegramDelivery
from .services import notify


def create_reminders():
    now = timezone.now()
    lessons = Lesson.objects.filter(
        status="scheduled",
        starts_at__gt=now,
        starts_at__lte=now + timedelta(minutes=15),
    ).select_related("group__teacher")

    for lesson in lessons:
        users = [lesson.group.teacher]
        for membership in lesson.group.memberships.select_related("student"):
            users.append(membership.student)
        for user in users:
            start = timezone.localtime(lesson.starts_at).strftime("%H:%M")
            notify(
                user,
                f"Скоро занятие «{lesson.title}», начало в {start}.",
                f"/lessons/{lesson.pk}/",
                f"lesson:{lesson.pk}:reminder",
            )

    tasks = Assignment.objects.filter(
        deadline__gt=now,
        deadline__lte=now + timedelta(hours=24),
    ).select_related("group")
    for task in tasks:
        submitted_ids = task.submissions.values_list("student_id", flat=True)
        memberships = task.group.memberships.exclude(
            student_id__in=submitted_ids
        ).select_related("student")
        for membership in memberships:
            deadline = timezone.localtime(task.deadline).strftime("%d.%m %H:%M")
            notify(
                membership.student,
                f"Приближается дедлайн «{task.title}»: {deadline}.",
                f"/assignments/{task.pk}/",
                f"assignment:{task.pk}:reminder",
            )

    inactive_sessions = StudentLessonSession.objects.filter(
        left_at__isnull=True,
        last_activity__lt=now - timedelta(seconds=90),
    )
    for session in inactive_sessions:

        StudentLessonSession.objects.filter(
            pk=session.pk,
            left_at__isnull=True,
            last_activity=session.last_activity,
        ).update(left_at=session.last_activity)


@transaction.atomic
def claim_delivery():
    now = timezone.now()
    ready = Q(status="pending", next_attempt_at__lte=now)
    abandoned = Q(status="sending", locked_at__lt=now - timedelta(minutes=5))
    delivery = (
        TelegramDelivery.objects
        .filter(
            ready | abandoned,
        )
        .order_by("pk")
        .first()
    )
    if not delivery:
        return None

    delivery.status = "sending"
    delivery.locked_at = now
    delivery.attempts += 1
    delivery.save(update_fields=["status", "locked_at", "attempts"])
    return delivery.pk, delivery.attempts


def delivery_payload(delivery_id):
    delivery = TelegramDelivery.objects.select_related("notification").get(
        pk=delivery_id
    )
    notification = delivery.notification
    link = TelegramLink.objects.filter(user_id=notification.recipient_id).first()
    if not link:
        return None
    text = notification.text + "\n" + settings.SITE_URL + notification.url
    return link.chat_id, text


def finish_delivery(delivery_id, attempt, status, error="", delay=0):
    TelegramDelivery.objects.filter(
        pk=delivery_id,
        status="sending",
        attempts=attempt,
    ).update(
        status=status,
        last_error=error[:300],
        locked_at=None,
        next_attempt_at=timezone.now() + timedelta(seconds=delay),
    )


async def send_pending(bot, limit=100):
    for _ in range(limit):
        claim = await sync_to_async(claim_delivery)()
        if claim is None:
            break
        delivery_id, attempts = claim
        payload = await sync_to_async(delivery_payload)(delivery_id)
        if payload is None:
            await sync_to_async(finish_delivery)(delivery_id, attempts, "skipped")
            continue

        chat_id, text = payload
        status = "sent"
        error = ""
        delay = 0
        try:
            await bot.send_message(chat_id=chat_id, text=text)
        except TelegramForbiddenError:
            status = "failed"
            error = "Бот заблокирован пользователем"
        except TelegramRetryAfter as exception:
            status = "pending"
            error = "Telegram просит подождать"
            delay = exception.retry_after + 1
        except Exception as exception:

            error = type(exception).__name__
            status = "pending"
            if attempts >= 5:
                status = "failed"
            delay = 30 * 2 ** min(attempts, 7)
            delay = min(delay, 3600)

        await sync_to_async(finish_delivery)(
            delivery_id, attempts, status, error, delay
        )
