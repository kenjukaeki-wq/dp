from django import forms
from .models import StudyGroup, Lesson, Material


class GroupForm(forms.ModelForm):
    class Meta:
        model = StudyGroup
        fields = ("title", "description")


class JoinForm(forms.Form):
    code = forms.CharField(label="Код приглашения", max_length=20)

    def clean_code(self):
        return self.cleaned_data["code"].strip().upper()


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = (
            "title",
            "topic",
            "description",
            "starts_at",
            "ends_at",
            "meeting_url",
        )
        widgets = {
            field: forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}
            )
            for field in ("starts_at", "ends_at")
        }


class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ("title", "file", "url")


class PollForm(forms.Form):
    question = forms.CharField(label="Вопрос", max_length=300)
    options = forms.CharField(
        label="Варианты ответа — каждый с новой строки",
        widget=forms.Textarea,
        help_text="От 2 до 6 вариантов, до 200 символов каждый.",
    )

    def clean_options(self):
        values = [
            x.strip() for x in self.cleaned_data["options"].splitlines() if x.strip()
        ]
        if (
            not 2 <= len(values) <= 6
            or any(len(x) > 200 for x in values)
            or len(values) != len(set(values))
        ):
            raise forms.ValidationError(
                "Укажите 2–6 разных вариантов длиной до 200 символов."
            )
        return values
