from django.contrib import admin
from accounts.admin import ReadOnlyAdmin
from .models import (
    StudyGroup,
    GroupMembership,
    Lesson,
    Material,
    StudentLessonSession,
    ChatMessage,
    RaisedHand,
    Poll,
    PollOption,
    PollVote,
)

for model in (
    StudyGroup,
    GroupMembership,
    Lesson,
    Material,
    StudentLessonSession,
    ChatMessage,
    RaisedHand,
    Poll,
    PollOption,
    PollVote,
):
    admin.site.register(model, ReadOnlyAdmin)
