from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command, CommandStart
from aiogram.filters.command import CommandObject
from aiogram.types import Message
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from accounts.models import TelegramLink
from accounts.services import link_telegram
from education.access import groups_for
from education.models import Lesson
from assignments.models import Assignment, Submission

router = Router()


@sync_to_async
def account_summary(chat_id, kind):
    link = TelegramLink.objects.select_related("user").filter(chat_id=chat_id).first()
    if not link:
        return "Сначала привяжите Telegram на сайте: Профиль → Подключить Telegram."
    user = link.user
    groups = groups_for(user)
    if kind == "lessons":
        rows = Lesson.objects.filter(
            group__in=groups,
            status__in=["scheduled", "live"],
            ends_at__gte=timezone.now(),
        ).select_related("group")[:10]
        lines = [
            f"{x.group.title} · {x.title}\n{timezone.localtime(x.starts_at):%d.%m %H:%M}\n{settings.SITE_URL}/lessons/{x.pk}/"
            for x in rows
        ]
    elif kind in ("tasks", "deadlines"):
        rows = Assignment.objects.filter(group__in=groups, deadline__gte=timezone.now())
        if not user.is_teacher:
            rows = rows.exclude(submissions__student=user)
        lines = [
            f"{x.title}\nДо {timezone.localtime(x.deadline):%d.%m %H:%M}\n{settings.SITE_URL}/assignments/{x.pk}/"
            for x in rows[:10]
        ]
    else:
        rows = (
            Submission.objects.filter(student=user, graded_at__isnull=False)
            .select_related("assignment")
            .order_by("-graded_at")[:10]
        )
        lines = [
            f"{x.assignment.title}: {x.score}/{x.assignment.max_score}" for x in rows
        ]
    return ("\n\n".join(lines) or "Пока ничего нет.")[:4000]


@router.message(CommandStart())
async def start(message: Message, command: CommandObject):
    if message.chat.type != "private":
        await message.answer("Откройте личный диалог с ботом.")
        return
    if command.args:
        try:
            await sync_to_async(link_telegram)(command.args, message.from_user.id)
        except ValidationError as exc:
            await message.answer("; ".join(exc.messages))
            return
        except IntegrityError:
            await message.answer(
                "Не удалось привязать аккаунт. Создайте новую ссылку в профиле."
            )
            return
        await message.answer(
            "Telegram подключён. Здесь будут появляться уведомления EduPlatform."
        )
    await message.answer(
        "/lessons — ближайшие занятия\n/tasks — задания без ответа\n/deadlines — дедлайны\n/grades — последние оценки\n/unlink — отключить Telegram"
    )


@router.message(Command("lessons", "tasks", "deadlines", "grades"))
async def summary(message: Message, command: CommandObject):
    if message.chat.type == "private":
        await message.answer(
            await account_summary(message.from_user.id, command.command)
        )


@router.message(Command("unlink"))
async def unlink(message: Message):
    if message.chat.type == "private":
        await sync_to_async(
            lambda: TelegramLink.objects.filter(chat_id=message.from_user.id).delete()
        )()
        await message.answer(
            "Telegram отключён. Повторная привязка доступна в профиле сайта."
        )


async def run():
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    async with Bot(settings.TELEGRAM_BOT_TOKEN) as bot:
        await dispatcher.start_polling(
            bot, allowed_updates=dispatcher.resolve_used_update_types()
        )
