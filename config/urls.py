from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import path
from accounts import views as accounts
from education import views as edu
from assignments import views as tasks
from notifications import views as notices

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", edu.dashboard, name="dashboard"),
    path(
        "accounts/login/",
        auth.LoginView.as_view(template_name="accounts/login.html"),
        name="login",
    ),
    path("accounts/logout/", auth.LogoutView.as_view(), name="logout"),
    path("accounts/register/", accounts.register, name="register"),
    path("accounts/profile/", accounts.profile, name="profile"),
    path(
        "accounts/telegram/connect/", accounts.telegram_connect, name="telegram_connect"
    ),
    path(
        "accounts/telegram/disconnect/",
        accounts.telegram_disconnect,
        name="telegram_disconnect",
    ),
    path("groups/create/", edu.group_create, name="group_create"),
    path("groups/join/", edu.group_join, name="group_join"),
    path("groups/<int:pk>/", edu.group_detail, name="group_detail"),
    path(
        "groups/<int:pk>/rotate-code/", edu.group_rotate_code, name="group_rotate_code"
    ),
    path("groups/<int:group_id>/lessons/new/", edu.lesson_create, name="lesson_create"),
    path(
        "groups/<int:group_id>/materials/new/",
        edu.material_create,
        name="material_create",
    ),
    path(
        "groups/<int:group_id>/lessons/<int:lesson_id>/materials/new/",
        edu.material_create,
        name="lesson_material_create",
    ),
    path(
        "materials/<int:pk>/download/", edu.material_download, name="material_download"
    ),
    path("lessons/<int:pk>/", edu.lesson_detail, name="lesson_detail"),
    path("lessons/<int:pk>/state/", edu.lesson_snapshot, name="lesson_snapshot"),
    path("lessons/<int:pk>/attendance/", edu.attendance, name="attendance"),
    path(
        "lessons/<int:pk>/actions/<str:action>/",
        edu.lesson_action,
        name="lesson_action",
    ),
    path("lessons/<int:lesson_id>/polls/new/", edu.poll_create, name="poll_create"),
    path(
        "lessons/<int:lesson_id>/polls/<int:pk>/close/",
        edu.poll_close,
        name="poll_close",
    ),
    path(
        "groups/<int:group_id>/assignments/new/",
        tasks.assignment_create,
        name="assignment_create",
    ),
    path("assignments/<int:pk>/", tasks.assignment_detail, name="assignment_detail"),
    path(
        "submissions/<int:pk>/grade/", tasks.submission_grade, name="submission_grade"
    ),
    path(
        "submissions/<int:pk>/download/",
        tasks.submission_download,
        name="submission_download",
    ),
    path(
        "attachments/<int:pk>/download/",
        tasks.attachment_download,
        name="attachment_download",
    ),
    path("notifications/", notices.inbox, name="notifications"),
    path("notifications/read-all/", notices.read_all, name="notifications_read_all"),
    path("notifications/<int:pk>/read/", notices.read, name="notification_read"),
]
