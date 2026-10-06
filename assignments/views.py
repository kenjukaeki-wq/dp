from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from education.access import require_access, require_teacher
from education.models import StudyGroup
from education.views import file_response
from .forms import AssignmentForm, SubmissionForm, GradeForm
from .models import Assignment, AssignmentAttachment, Submission
from .services import announce_assignment, submit, grade


@login_required
def assignment_create(request, group_id):
    group = get_object_or_404(StudyGroup, pk=group_id)
    require_teacher(request.user, group)
    form = AssignmentForm(
        request.POST or None,
        request.FILES or None,
        group=group,
        instance=Assignment(group=group),
    )
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            assignment = form.save()
            if form.cleaned_data["attachment"]:
                AssignmentAttachment.objects.create(
                    assignment=assignment, file=form.cleaned_data["attachment"]
                )
            announce_assignment(assignment)
        return redirect("assignment_detail", pk=assignment.pk)
    return render(
        request, "form.html", {"form": form, "title": f"Новое задание · {group.title}"}
    )


@login_required
def assignment_detail(request, pk):
    assignment = get_object_or_404(Assignment.objects.select_related("group"), pk=pk)
    require_access(request.user, assignment.group)
    teacher = assignment.group.teacher_id == request.user.pk
    item = Submission.objects.filter(
        assignment=assignment, student=request.user
    ).first()
    editable = (
        not teacher
        and timezone.now() <= assignment.deadline
        and not (item and item.graded_at)
    )
    form = (
        SubmissionForm(
            request.POST or None,
            request.FILES or None,
            instance=item or Submission(assignment=assignment, student=request.user),
        )
        if not teacher
        else None
    )
    if request.method == "POST":
        if not editable:
            raise PermissionDenied("Изменение ответа недоступно.")
        if form.is_valid():
            try:
                submit(
                    request.user,
                    pk,
                    form.cleaned_data["text"],
                    request.FILES.get("file"),
                    form.cleaned_data["clear_file"],
                )
                messages.success(request, "Работа отправлена.")
                return redirect("assignment_detail", pk=pk)
            except ValidationError as exc:
                form.add_error(None, exc)
    return render(
        request,
        "assignments/detail.html",
        {
            "assignment": assignment,
            "submission": item,
            "submissions": (
                assignment.submissions.select_related("student") if teacher else []
            ),
            "teacher": teacher,
            "form": form,
            "editable": editable,
        },
    )


@login_required
def submission_grade(request, pk):
    item = get_object_or_404(
        Submission.objects.select_related("assignment__group", "student"), pk=pk
    )
    require_teacher(request.user, item.assignment.group)
    form = GradeForm(
        request.POST or None,
        max_score=item.assignment.max_score,
        initial={"score": item.score, "feedback": item.feedback},
    )
    if request.method == "POST" and form.is_valid():
        grade(
            request.user, pk, form.cleaned_data["score"], form.cleaned_data["feedback"]
        )
        messages.success(request, "Оценка сохранена.")
        return redirect("assignment_detail", pk=item.assignment_id)
    return render(request, "assignments/grade.html", {"submission": item, "form": form})


@login_required
def attachment_download(request, pk):
    item = get_object_or_404(
        AssignmentAttachment.objects.select_related("assignment__group"), pk=pk
    )
    require_access(request.user, item.assignment.group)
    return file_response(item.file)


@login_required
def submission_download(request, pk):
    item = get_object_or_404(
        Submission.objects.select_related("assignment__group"), pk=pk
    )
    require_access(request.user, item.assignment.group)
    if request.user.pk not in (item.student_id, item.assignment.group.teacher_id):
        raise PermissionDenied("Работу видят только автор и преподаватель.")
    if not item.file:
        from django.http import Http404

        raise Http404
    return file_response(item.file)
