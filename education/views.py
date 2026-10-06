from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from .access import groups_for, require_access, require_teacher
from .forms import GroupForm, JoinForm, LessonForm, MaterialForm, PollForm
from .models import StudyGroup, GroupMembership, Lesson, Material, invitation_code
from .services import (
    change_lesson_status,
    create_poll,
    close_poll,
    attendance_report,
    lesson_state,
)
from assignments.models import Assignment


@login_required
def dashboard(request):
    groups = groups_for(request.user).select_related("teacher")
    lessons = (
        Lesson.objects.filter(group__in=groups)
        .filter(Q(status="live") | Q(status="scheduled", ends_at__gte=timezone.now()))
        .select_related("group")
        .order_by("starts_at")[:12]
    )
    assignments = Assignment.objects.filter(
        group__in=groups, deadline__gte=timezone.now()
    ).select_related("group")[:8]
    return render(
        request,
        "education/dashboard.html",
        {"groups": groups, "lessons": lessons, "assignments": assignments},
    )


@login_required
def group_create(request):
    require_teacher(request.user)
    form = GroupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        group = form.save(commit=False)
        group.teacher = request.user
        group.save()
        return redirect("group_detail", pk=group.pk)
    return render(request, "form.html", {"form": form, "title": "Новая группа"})


@login_required
def group_join(request):
    if request.user.is_teacher:
        raise PermissionDenied("Вступление по коду доступно ученикам.")
    form = JoinForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        group = StudyGroup.objects.filter(invite_code=form.cleaned_data["code"]).first()
        if group:
            _, created = GroupMembership.objects.get_or_create(
                group=group, student=request.user
            )
            messages.success(
                request,
                "Вы присоединились к группе." if created else "Вы уже в этой группе.",
            )
            return redirect("group_detail", pk=group.pk)
        form.add_error("code", "Группа с таким кодом не найдена.")
    return render(
        request, "form.html", {"form": form, "title": "Присоединиться к группе"}
    )


@login_required
def group_detail(request, pk):
    group = get_object_or_404(StudyGroup.objects.select_related("teacher"), pk=pk)
    require_access(request.user, group)
    return render(
        request,
        "education/group.html",
        {
            "group": group,
            "members": group.memberships.select_related("student"),
            "lessons": group.lessons.all(),
            "materials": group.materials.filter(lesson__isnull=True),
            "assignments": group.assignments.all(),
        },
    )


@login_required
@require_POST
def group_rotate_code(request, pk):
    group = get_object_or_404(StudyGroup, pk=pk)
    require_teacher(request.user, group)
    group.invite_code = invitation_code()
    group.save(update_fields=["invite_code"])
    messages.success(request, "Код обновлён. Старый код больше не действует.")
    return redirect("group_detail", pk=pk)


@login_required
def lesson_create(request, group_id):
    group = get_object_or_404(StudyGroup, pk=group_id)
    require_teacher(request.user, group)
    form = LessonForm(request.POST or None, instance=Lesson(group=group))
    if request.method == "POST" and form.is_valid():
        lesson = form.save()
        return redirect("lesson_detail", pk=lesson.pk)
    return render(
        request, "form.html", {"form": form, "title": f"Новое занятие · {group.title}"}
    )


@login_required
def lesson_detail(request, pk):
    lesson = get_object_or_404(Lesson.objects.select_related("group"), pk=pk)
    require_access(request.user, lesson.group)
    return render(
        request,
        "education/lesson.html",
        {
            "lesson": lesson,
            "materials": Material.objects.filter(group=lesson.group).filter(
                Q(lesson=lesson) | Q(lesson__isnull=True)
            ),
            "assignments": lesson.assignments.all(),
            "members": lesson.group.memberships.select_related("student"),
            "initial_state": lesson_state(request.user, pk),
        },
    )


@login_required
def lesson_snapshot(request, pk):
    lesson = get_object_or_404(Lesson.objects.select_related("group"), pk=pk)
    require_access(request.user, lesson.group)
    return JsonResponse(lesson_state(request.user, pk))


@login_required
@require_POST
def lesson_action(request, pk, action):
    get_object_or_404(Lesson, pk=pk)
    try:
        change_lesson_status(request.user, pk, action)
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("lesson_detail", pk=pk)


@login_required
def material_create(request, group_id, lesson_id=None):
    group = get_object_or_404(StudyGroup, pk=group_id)
    require_teacher(request.user, group)
    lesson = get_object_or_404(Lesson, pk=lesson_id, group=group) if lesson_id else None
    form = MaterialForm(
        request.POST or None,
        request.FILES or None,
        instance=Material(group=group, lesson=lesson),
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        return (
            redirect("lesson_detail", pk=lesson.pk)
            if lesson
            else redirect("group_detail", pk=group.pk)
        )
    return render(request, "form.html", {"form": form, "title": "Добавить материал"})


def file_response(file):
    response = FileResponse(
        file.open("rb"),
        as_attachment=True,
        filename=file.name.rsplit("/", 1)[-1],
        content_type="application/octet-stream",
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
def material_download(request, pk):
    item = get_object_or_404(Material.objects.select_related("group"), pk=pk)
    require_access(request.user, item.group)
    if not item.file:
        from django.http import Http404

        raise Http404
    return file_response(item.file)


@login_required
def poll_create(request, lesson_id):
    lesson = get_object_or_404(Lesson.objects.select_related("group"), pk=lesson_id)
    require_teacher(request.user, lesson.group)
    form = PollForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            create_poll(
                request.user,
                lesson.pk,
                form.cleaned_data["question"],
                form.cleaned_data["options"],
            )
            return redirect("lesson_detail", pk=lesson.pk)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request, "form.html", {"form": form, "title": "Запустить быстрый опрос"}
    )


@login_required
@require_POST
def poll_close(request, lesson_id, pk):
    get_object_or_404(Lesson, pk=lesson_id)
    close_poll(request.user, lesson_id, pk)
    return redirect("lesson_detail", pk=lesson_id)


@login_required
def attendance(request, pk):
    lesson = get_object_or_404(Lesson.objects.select_related("group"), pk=pk)
    require_teacher(request.user, lesson.group)
    return render(
        request,
        "education/attendance.html",
        {"lesson": lesson, "rows": attendance_report(lesson)},
    )
