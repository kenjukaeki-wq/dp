import asyncio
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Запустить aiogram-бота (один процесс polling на один токен)."

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError("Задайте TELEGRAM_BOT_TOKEN в .env.")
        from notifications.bot.runner import run

        asyncio.run(run())
