# Generated for F2 (education pedagogical layer).
#
# Adds first-class pedagogical fields to LOMEducational (Riobamba LOM section 5
# extension) plus their modeltranslation language columns, and tightens
# typical_learning_time to an ISO-8601 validated value.
#
# NOTE: the *_es / *_en / *_qu language columns below mirror exactly what
# `makemigrations` emits for django-modeltranslation-registered fields
# (prerequisites, competencies, suggested_activities). If you regenerate this
# migration in Docker it should be a no-op.

import apps.education.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("education", "0005_alter_lomeducational_learning_resource_type"),
    ]

    operations = [
        # --- Base pedagogical fields ---
        migrations.AddField(
            model_name="lomeducational",
            name="competencies",
            field=models.TextField(
                blank=True,
                help_text="Competencies or skills this resource helps develop",
                verbose_name="competencies",
            ),
        ),
        migrations.AddField(
            model_name="lomeducational",
            name="curriculum_alignment",
            field=models.CharField(
                blank=True,
                help_text="National-curriculum alignment (level / grade / subject)",
                max_length=300,
                verbose_name="curriculum alignment",
            ),
        ),
        migrations.AddField(
            model_name="lomeducational",
            name="learning_objectives",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="List of learning objectives (what a learner should achieve)",
                verbose_name="learning objectives",
            ),
        ),
        migrations.AddField(
            model_name="lomeducational",
            name="pedagogical_approach",
            field=models.CharField(
                blank=True,
                choices=[
                    ("expository", "Expository"),
                    ("inquiry", "Inquiry-based"),
                    ("constructivist", "Constructivist"),
                    ("project_based", "Project-based"),
                    ("collaborative", "Collaborative"),
                    ("gamified", "Gamified"),
                ],
                help_text="Suggested teaching strategy for this resource",
                max_length=30,
                verbose_name="pedagogical approach",
            ),
        ),
        migrations.AddField(
            model_name="lomeducational",
            name="prerequisites",
            field=models.TextField(
                blank=True,
                help_text="Prior knowledge or resources needed before using this object",
                verbose_name="prerequisites",
            ),
        ),
        migrations.AddField(
            model_name="lomeducational",
            name="suggested_activities",
            field=models.TextField(
                blank=True,
                help_text="Suggested classroom activities / reuse guidance for educators",
                verbose_name="suggested activities",
            ),
        ),
        # --- modeltranslation language columns (competencies) ---
        migrations.AddField(
            model_name="lomeducational",
            name="competencies_en",
            field=models.TextField(
                blank=True,
                help_text="Competencies or skills this resource helps develop",
                null=True,
                verbose_name="competencies",
            ),
        ),
        migrations.AddField(
            model_name="lomeducational",
            name="competencies_es",
            field=models.TextField(
                blank=True,
                help_text="Competencies or skills this resource helps develop",
                null=True,
                verbose_name="competencies",
            ),
        ),
        migrations.AddField(
            model_name="lomeducational",
            name="competencies_qu",
            field=models.TextField(
                blank=True,
                help_text="Competencies or skills this resource helps develop",
                null=True,
                verbose_name="competencies",
            ),
        ),
        # --- modeltranslation language columns (prerequisites) ---
        migrations.AddField(
            model_name="lomeducational",
            name="prerequisites_en",
            field=models.TextField(
                blank=True,
                help_text="Prior knowledge or resources needed before using this object",
                null=True,
                verbose_name="prerequisites",
            ),
        ),
        migrations.AddField(
            model_name="lomeducational",
            name="prerequisites_es",
            field=models.TextField(
                blank=True,
                help_text="Prior knowledge or resources needed before using this object",
                null=True,
                verbose_name="prerequisites",
            ),
        ),
        migrations.AddField(
            model_name="lomeducational",
            name="prerequisites_qu",
            field=models.TextField(
                blank=True,
                help_text="Prior knowledge or resources needed before using this object",
                null=True,
                verbose_name="prerequisites",
            ),
        ),
        # --- modeltranslation language columns (suggested_activities) ---
        migrations.AddField(
            model_name="lomeducational",
            name="suggested_activities_en",
            field=models.TextField(
                blank=True,
                help_text="Suggested classroom activities / reuse guidance for educators",
                null=True,
                verbose_name="suggested activities",
            ),
        ),
        migrations.AddField(
            model_name="lomeducational",
            name="suggested_activities_es",
            field=models.TextField(
                blank=True,
                help_text="Suggested classroom activities / reuse guidance for educators",
                null=True,
                verbose_name="suggested activities",
            ),
        ),
        migrations.AddField(
            model_name="lomeducational",
            name="suggested_activities_qu",
            field=models.TextField(
                blank=True,
                help_text="Suggested classroom activities / reuse guidance for educators",
                null=True,
                verbose_name="suggested activities",
            ),
        ),
        # --- Tighten typical_learning_time to ISO-8601 ---
        migrations.AlterField(
            model_name="lomeducational",
            name="typical_learning_time",
            field=models.CharField(
                blank=True,
                help_text='Approximate time it takes to work with this learning object (ISO-8601, e.g. "PT30M")',
                max_length=50,
                validators=[apps.education.models.validate_iso8601_duration],
                verbose_name="typical learning time",
            ),
        ),
    ]
