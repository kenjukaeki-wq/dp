import asyncio
from asgiref.sync import sync_to_async
from aiogram import Bot
from django.conf import settings
from django.core.management.base import BaseCommand
from notifications.worker import create_reminders, send_pending


class Command(BaseCommand):
    help = "Напоминания, закрытие неактивных сессий, отправка Telegram. Без --once работает постоянно."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        async def loop():
            bot = (
                Bot(settings.TELEGRAM_BOT_TOKEN)
                if settings.TELEGRAM_BOT_TOKEN
                else None
            )
            try:
                while True:
                    await sync_to_async(create_reminders)()
                    if bot:
                        await send_pending(bot)
                    if options["once"]:
                        break
                    await asyncio.sleep(30)
            finally:
                if bot:
                    await bot.session.close()

        asyncio.run(loop())
