import django.core.validators
import django.db.models.deletion
import education.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('education', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Assignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='Название')),
                ('description', models.TextField(verbose_name='Описание')),
                ('deadline', models.DateTimeField(verbose_name='Дедлайн')),
                ('max_score', models.PositiveIntegerField(default=100, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(10000)], verbose_name='Максимальный балл')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignments', to='education.studygroup')),
                ('lesson', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assignments', to='education.lesson')),
            ],
            options={
                'ordering': ['deadline'],
            },
        ),
        migrations.CreateModel(
            name='AssignmentAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to=education.models.private_upload, validators=[education.models.validate_file], verbose_name='Файл')),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='assignments.assignment')),
            ],
        ),
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField(blank=True, verbose_name='Ответ')),
                ('file', models.FileField(blank=True, upload_to=education.models.private_upload, validators=[education.models.validate_file], verbose_name='Файл')),
                ('submitted_at', models.DateTimeField()),
                ('score', models.PositiveIntegerField(blank=True, null=True, verbose_name='Оценка')),
                ('feedback', models.TextField(blank=True, verbose_name='Комментарий преподавателя')),
                ('graded_at', models.DateTimeField(blank=True, null=True)),
                ('revision', models.PositiveIntegerField(default=0)),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submissions', to='assignments.assignment')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submissions', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name='assignment',
            constraint=models.CheckConstraint(condition=models.Q(('max_score__gte', 1), ('max_score__lte', 10000)), name='valid_max_score'),
        ),
        migrations.AddConstraint(
            model_name='submission',
            constraint=models.UniqueConstraint(fields=('assignment', 'student'), name='one_submission'),
        ),
    ]
