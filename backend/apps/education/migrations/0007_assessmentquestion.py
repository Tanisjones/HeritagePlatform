# Generated for F2.c (education interoperability layer).
#
# Adds the AssessmentQuestion model (quiz/exam questions attached to a
# LOMGeneral, feeding the QTI 2.1 export) plus its modeltranslation language
# columns for the translated fields `prompt` and `feedback`.
#
# NOTE: the CreateModel + *_es / *_en AddField columns below mirror what
# `makemigrations` emits for a new model whose `prompt`/`feedback` fields are
# registered with django-modeltranslation. The project configures only es/en
# (settings LANGUAGES), so there are no *_qu columns. If you regenerate this
# migration in Docker it should be a no-op.

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("education", "0006_lomeducational_pedagogical_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="AssessmentQuestion",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("order", models.IntegerField(default=0, help_text="Display order of this question within the assessment", verbose_name="order")),
                (
                    "question_type",
                    models.CharField(
                        choices=[
                            ("single_choice", "Single choice"),
                            ("multiple_choice", "Multiple choice"),
                            ("true_false", "True/False"),
                            ("short_answer", "Short answer"),
                        ],
                        default="single_choice",
                        help_text="Kind of question / interaction",
                        max_length=20,
                        verbose_name="question type",
                    ),
                ),
                ("prompt", models.TextField(help_text="The question text presented to the learner", verbose_name="prompt")),
                (
                    "choices",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Answer options for choice questions (list of {id, text, correct})",
                        verbose_name="choices",
                    ),
                ),
                (
                    "correct_response",
                    models.TextField(
                        blank=True,
                        help_text="Expected answer for short-answer / true-false questions",
                        verbose_name="correct response",
                    ),
                ),
                ("feedback", models.TextField(blank=True, help_text="Feedback shown to the learner after answering", verbose_name="feedback")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "lom_general",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="questions",
                        to="education.lomgeneral",
                        verbose_name="LOM general",
                    ),
                ),
            ],
            options={
                "verbose_name": "Assessment Question",
                "verbose_name_plural": "Assessment Questions",
                "ordering": ["order"],
            },
        ),
        # --- modeltranslation language columns (prompt) ---
        migrations.AddField(
            model_name="assessmentquestion",
            name="prompt_en",
            field=models.TextField(
                help_text="The question text presented to the learner",
                null=True,
                verbose_name="prompt",
            ),
        ),
        migrations.AddField(
            model_name="assessmentquestion",
            name="prompt_es",
            field=models.TextField(
                help_text="The question text presented to the learner",
                null=True,
                verbose_name="prompt",
            ),
        ),
        # --- modeltranslation language columns (feedback) ---
        migrations.AddField(
            model_name="assessmentquestion",
            name="feedback_en",
            field=models.TextField(
                blank=True,
                help_text="Feedback shown to the learner after answering",
                null=True,
                verbose_name="feedback",
            ),
        ),
        migrations.AddField(
            model_name="assessmentquestion",
            name="feedback_es",
            field=models.TextField(
                blank=True,
                help_text="Feedback shown to the learner after answering",
                null=True,
                verbose_name="feedback",
            ),
        ),
    ]
