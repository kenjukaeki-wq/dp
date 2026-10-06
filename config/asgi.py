import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.asgi import get_asgi_application


http_application = get_asgi_application()

from django.conf import settings
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.urls import path
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from education.consumers import LessonConsumer
from notifications.consumers import NotificationConsumer



if settings.DEBUG:
    http_application = ASGIStaticFilesHandler(http_application)

websocket_urls = [
    path("ws/lessons/<int:lesson_id>/", LessonConsumer.as_asgi()),
    path("ws/notifications/", NotificationConsumer.as_asgi()),
]

application = ProtocolTypeRouter(
    {
        "http": http_application,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urls))
        ),
    }
)
