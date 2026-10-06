import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from .models import Notification, TelegramDelivery

logger = logging.getLogger(__name__)


def broadcast(group_name, payload):
    channel_layer = get_channel_layer()
    message = {"type": "event", "payload": payload}
    try:
        async_to_sync(channel_layer.group_send)(group_name, message)
    except Exception:

        logger.exception("Не удалось отправить WebSocket-событие")


def after_commit(group_name, payload):

    def send():
        broadcast(group_name, payload)

    transaction.on_commit(send)


@transaction.atomic
def notify(user, text, url, event_key):


    notification, created = Notification.objects.get_or_create(
        recipient=user,
        event_key=event_key,
        defaults={"text": text[:500], "url": url},
    )
    if not created:
        return notification

    if hasattr(user, "telegram"):
        TelegramDelivery.objects.create(notification=notification)

    after_commit(
        f"user_{user.pk}",
        {
            "event": "notification.created",
            "text": notification.text,
            "url": url,
        },
    )
    return notification


def notify_group(group, text, url, event_key):
    for membership in group.memberships.select_related("student"):
        notify(membership.student, text, url, event_key)
