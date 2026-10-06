import django.db.models.deletion
import education.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Lesson',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=160, verbose_name='Название')),
                ('topic', models.CharField(max_length=200, verbose_name='Тема')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('starts_at', models.DateTimeField(verbose_name='Начало')),
                ('ends_at', models.DateTimeField(verbose_name='Окончание')),
                ('meeting_url', models.URLField(blank=True, validators=[education.models.validate_http_url], verbose_name='Ссылка на видеоконференцию')),
                ('status', models.CharField(choices=[('scheduled', 'Запланировано'), ('live', 'Идёт занятие'), ('finished', 'Завершено'), ('cancelled', 'Отменено')], default='scheduled', max_length=12)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'ordering': ['starts_at'],
            },
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=2000)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chat_messages', to='education.lesson')),
            ],
            options={
                'ordering': ['created_at', 'id'],
            },
        ),
        migrations.CreateModel(
            name='Poll',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.CharField(max_length=300, verbose_name='Вопрос')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='polls', to='education.lesson')),
            ],
        ),
        migrations.CreateModel(
            name='PollOption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=200)),
                ('poll', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='options', to='education.poll')),
            ],
        ),
        migrations.CreateModel(
            name='PollVote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('option', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='votes', to='education.polloption')),
                ('poll', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='votes', to='education.poll')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='RaisedHand',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('raised_at', models.DateTimeField(auto_now_add=True)),
                ('lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='hands', to='education.lesson')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='StudentLessonSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('connection_id', models.CharField(max_length=255, unique=True)),
                ('joined_at', models.DateTimeField()),
                ('last_activity', models.DateTimeField()),
                ('left_at', models.DateTimeField(blank=True, null=True)),
                ('lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sessions', to='education.lesson')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='StudyGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=160, verbose_name='Название')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('invite_code', models.CharField(default=education.models.invitation_code, editable=False, max_length=20, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('teacher', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='teaching_groups', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Material',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='Название')),
                ('file', models.FileField(blank=True, upload_to=education.models.private_upload, validators=[education.models.validate_file], verbose_name='Файл')),
                ('url', models.URLField(blank=True, validators=[education.models.validate_http_url], verbose_name='Ссылка')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('lesson', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='materials', to='education.lesson')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='materials', to='education.studygroup')),
            ],
        ),
        migrations.AddField(
            model_name='lesson',
            name='group',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lessons', to='education.studygroup'),
        ),
        migrations.CreateModel(
            name='GroupMembership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to=settings.AUTH_USER_MODEL)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='education.studygroup')),
            ],
        ),
        migrations.AddConstraint(
            model_name='poll',
            constraint=models.UniqueConstraint(condition=models.Q(('is_active', True)), fields=('lesson',), name='one_active_poll'),
        ),
        migrations.AddConstraint(
            model_name='pollvote',
            constraint=models.UniqueConstraint(fields=('poll', 'student'), name='one_vote_per_student'),
        ),
        migrations.AddConstraint(
            model_name='raisedhand',
            constraint=models.UniqueConstraint(fields=('lesson', 'student'), name='unique_raised_hand'),
        ),
        migrations.AddIndex(
            model_name='studentlessonsession',
            index=models.Index(fields=['lesson', 'student'], name='education_s_lesson__056ce3_idx'),
        ),
        migrations.AddIndex(
            model_name='lesson',
            index=models.Index(fields=['status', 'starts_at'], name='education_l_status_62f55d_idx'),
        ),
        migrations.AddConstraint(
            model_name='lesson',
            constraint=models.CheckConstraint(condition=models.Q(('ends_at__gt', models.F('starts_at'))), name='lesson_end_after_start'),
        ),
        migrations.AddConstraint(
            model_name='groupmembership',
            constraint=models.UniqueConstraint(fields=('group', 'student'), name='unique_group_student'),
        ),
    ]
