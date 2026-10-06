from django.contrib import admin
from accounts.admin import ReadOnlyAdmin
from .models import Assignment, AssignmentAttachment, Submission

for model in (Assignment, AssignmentAttachment, Submission):
    admin.site.register(model, ReadOnlyAdmin)
