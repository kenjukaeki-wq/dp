from django import forms
from django.core.validators import MaxValueValidator
from education.models import validate_file
from .models import Assignment, Submission


class AssignmentForm(forms.ModelForm):
    attachment = forms.FileField(
        label="Файл задания", required=False, validators=[validate_file]
    )

    class Meta:
        model = Assignment
        fields = ("title", "description", "lesson", "deadline", "max_score")
        widgets = {
            "deadline": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}
            )
        }

    def __init__(self, *args, group, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lesson"].queryset = group.lessons.all()


class SubmissionForm(forms.ModelForm):
    clear_file = forms.BooleanField(
        label="Удалить ранее прикреплённый файл", required=False
    )

    class Meta:
        model = Submission
        fields = ("text", "file")
        widgets = {"file": forms.FileInput()}

    def clean(self):
        data = super().clean()
        if (
            data.get("clear_file")
            and not data.get("text", "").strip()
            and not self.files.get("file")
        ):
            raise forms.ValidationError(
                "После удаления файла должен остаться текст ответа."
            )
        return data


class GradeForm(forms.Form):
    score = forms.IntegerField(label="Оценка", min_value=0)
    feedback = forms.CharField(
        label="Комментарий", required=False, widget=forms.Textarea
    )

    def __init__(self, *args, max_score, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["score"].max_value = max_score
        self.fields["score"].validators.append(MaxValueValidator(max_score))
        self.fields["score"].widget.attrs["max"] = max_score
