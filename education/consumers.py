import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError

from .access import can_access
from .models import Lesson
from . import services


class LessonConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.user = self.scope["user"]
        self.lesson_id = self.scope["url_route"]["kwargs"]["lesson_id"]
        self.joined_groups = []

        lesson = (
            Lesson.objects.select_related("group").filter(pk=self.lesson_id).first()
        )
        if not lesson or not can_access(self.user, lesson.group):
            self.close(code=4403)
            return


        self.joined_groups.append(f"lesson_{self.lesson_id}")
        if lesson.group.teacher_id == self.user.pk:
            self.joined_groups.append(f"lesson_{self.lesson_id}_teacher")

        for group_name in self.joined_groups:
            async_to_sync(self.channel_layer.group_add)(group_name, self.channel_name)

        self.accept()
        services.heartbeat(self.user, self.lesson_id, self.channel_name)
        self.send_json(services.lesson_state(self.user, self.lesson_id))

    def receive(self, text_data=None, bytes_data=None, **kwargs):
        if not text_data or len(text_data) > 8192:
            self.send_json(
                {"event": "error", "text": "Слишком большое или пустое сообщение."}
            )
            return
        try:
            data = json.loads(text_data)
        except ValueError:
            self.send_json({"event": "error", "text": "Некорректный JSON."})
            return
        self.receive_json(data)

    def receive_json(self, data, **kwargs):
        try:
            if not isinstance(data, dict):
                raise ValidationError("Ожидается объект JSON.")
            action = data.get("action")

            if action == "heartbeat":
                services.heartbeat(self.user, self.lesson_id, self.channel_name)
                self.send_json({"event": "heartbeat.ok"})

            elif action == "state":
                self.send_json(services.lesson_state(self.user, self.lesson_id))

            elif action == "chat":
                services.chat(self.user, self.lesson_id, data.get("text"))

            elif action == "hand":
                services.set_hand(self.user, self.lesson_id, data.get("raised"))

            elif action == "vote":
                poll_id = int(data.get("poll"))
                option_id = int(data.get("option"))
                services.vote(self.user, self.lesson_id, poll_id, option_id)
                self.send_json(services.lesson_state(self.user, self.lesson_id))

            else:
                raise ValidationError("Неизвестное действие.")

        except PermissionDenied:
            self.close(code=4403)
        except ValidationError as error:
            self.send_json({"event": "error", "text": "; ".join(error.messages)})
        except (ValueError, TypeError, ObjectDoesNotExist):
            self.send_json({"event": "error", "text": "Некорректные данные."})

    def event(self, event):
        lesson = (
            Lesson.objects.select_related("group").filter(pk=self.lesson_id).first()
        )
        if not lesson or not can_access(self.user, lesson.group):
            self.close(code=4403)
            return
        self.send_json(event["payload"])

    def disconnect(self, code):
        services.close_session(self.channel_name)
        for group_name in getattr(self, "joined_groups", []):
            async_to_sync(self.channel_layer.group_discard)(
                group_name, self.channel_name
            )
