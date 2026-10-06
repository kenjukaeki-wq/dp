import hashlib
import secrets
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import TelegramToken, TelegramLink


def create_telegram_token(user):
    token = secrets.token_urlsafe(24)
    TelegramToken.objects.update_or_create(
        user=user,
        defaults={
            "digest": hashlib.sha256(token.encode()).hexdigest(),
            "expires_at": timezone.now() + timedelta(minutes=10),
        },
    )
    return token


@transaction.atomic
def link_telegram(token, chat_id):
    item = (
        TelegramToken.objects
        .filter(
            digest=hashlib.sha256(token.encode()).hexdigest(),
            expires_at__gt=timezone.now(),
        )
        .first()
    )
    if not item:
        raise ValidationError(
            "Ссылка недействительна или истекла. Создайте новую в профиле."
        )
    if (
        TelegramLink.objects.filter(chat_id=chat_id)
        .exclude(user_id=item.user_id)
        .exists()
    ):
        raise ValidationError("Этот Telegram уже связан с другим аккаунтом.")
    TelegramLink.objects.update_or_create(
        user_id=item.user_id, defaults={"chat_id": chat_id}
    )
    item.delete()
