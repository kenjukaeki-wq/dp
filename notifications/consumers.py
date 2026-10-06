from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer


class NotificationConsumer(JsonWebsocketConsumer):
    def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            self.close(code=4401)
            return
        self.group = f"user_{user.pk}"
        async_to_sync(self.channel_layer.group_add)(self.group, self.channel_name)
        self.accept()

    def receive(self, text_data=None, bytes_data=None, **kwargs):
        pass

    def event(self, event):
        self.send_json(event["payload"])

    def disconnect(self, code):
        if hasattr(self, "group"):
            async_to_sync(self.channel_layer.group_discard)(
                self.group, self.channel_name
            )
