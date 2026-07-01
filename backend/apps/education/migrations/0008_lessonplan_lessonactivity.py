import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("education", "0007_assessmentquestion"),
        ("heritage", "0012_heritageitem_main_image"),
        ("routes", "0003_alter_heritageroute_available_languages"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="LessonPlan",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("title", models.CharField(max_length=200, verbose_name="title")),
                ("summary", models.TextField(blank=True, verbose_name="summary")),
                (
                    "objectives",
                    models.JSONField(blank=True, default=list, verbose_name="learning objectives"),
                ),
                ("subject", models.CharField(blank=True, max_length=120, verbose_name="subject")),
                (
                    "grade_level",
                    models.CharField(blank=True, max_length=120, verbose_name="grade level"),
                ),
                (
                    "audience",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("teacher", "Teacher"),
                            ("author", "Author"),
                            ("learner", "Learner"),
                            ("manager", "Manager"),
                        ],
                        max_length=20,
                        verbose_name="audience",
                    ),
                ),
                (
                    "curriculum_alignment",
                    models.CharField(blank=True, max_length=300, verbose_name="curriculum alignment"),
                ),
                (
                    "pedagogical_approach",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("expository", "Expository"),
                            ("inquiry", "Inquiry-based"),
                            ("constructivist", "Constructivist"),
                            ("project_based", "Project-based"),
                            ("collaborative", "Collaborative"),
                            ("gamified", "Gamified"),
                        ],
                        max_length=30,
                        verbose_name="pedagogical approach",
                    ),
                ),
                (
                    "estimated_total_minutes",
                    models.IntegerField(blank=True, null=True, verbose_name="estimated total minutes"),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("review", "In review"),
                            ("published", "Published"),
                            ("archived", "Archived"),
                        ],
                        default="draft",
                        max_length=20,
                        verbose_name="status",
                    ),
                ),
                (
                    "visibility",
                    models.CharField(
                        choices=[
                            ("private", "Private"),
                            ("unlisted", "Unlisted"),
                            ("public", "Public"),
                        ],
                        default="private",
                        max_length=20,
                        verbose_name="visibility",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "author",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="lesson_plans",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="author",
                    ),
                ),
                (
                    "related_route",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="lesson_plans",
                        to="routes.heritageroute",
                        verbose_name="related route",
                    ),
                ),
            ],
            options={
                "verbose_name": "lesson plan",
                "verbose_name_plural": "lesson plans",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="LessonActivity",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("order", models.IntegerField(default=0, verbose_name="order")),
                ("title", models.CharField(max_length=200, verbose_name="title")),
                (
                    "activity_type",
                    models.CharField(
                        choices=[
                            ("hook", "Hook / engage"),
                            ("explore", "Explore"),
                            ("explain", "Explain"),
                            ("practice", "Practice"),
                            ("assess", "Assess"),
                            ("reflect", "Reflect"),
                        ],
                        default="explore",
                        max_length=20,
                        verbose_name="activity type",
                    ),
                ),
                ("instructions", models.TextField(blank=True, verbose_name="instructions")),
                (
                    "duration_minutes",
                    models.IntegerField(blank=True, null=True, verbose_name="duration (minutes)"),
                ),
                ("materials", models.TextField(blank=True, verbose_name="materials")),
                (
                    "educational_resource",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+", to="education.educationalresource",
                        verbose_name="educational resource",
                    ),
                ),
                (
                    "heritage_item",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+", to="heritage.heritageitem",
                        verbose_name="heritage item",
                    ),
                ),
                (
                    "lesson",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="activities", to="education.lessonplan",
                        verbose_name="lesson",
                    ),
                ),
                (
                    "lom_general",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+", to="education.lomgeneral",
                        verbose_name="quiz (LOM object)",
                    ),
                ),
                (
                    "route",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+", to="routes.heritageroute",
                        verbose_name="route",
                    ),
                ),
            ],
            options={
                "verbose_name": "lesson activity",
                "verbose_name_plural": "lesson activities",
                "ordering": ["order"],
            },
        ),
        migrations.AddConstraint(
            model_name="lessonactivity",
            constraint=models.UniqueConstraint(
                fields=("lesson", "order"), name="unique_activity_order_per_lesson"
            ),
        ),
    ]
