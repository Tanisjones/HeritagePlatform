import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai_services", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AIUsageRecord",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="created at")),
                ("operation", models.CharField(max_length=60, verbose_name="operation")),
                ("provider", models.CharField(max_length=40, verbose_name="provider")),
                ("model", models.CharField(max_length=120, verbose_name="model")),
                (
                    "input_tokens",
                    models.IntegerField(blank=True, null=True, verbose_name="input tokens"),
                ),
                (
                    "output_tokens",
                    models.IntegerField(blank=True, null=True, verbose_name="output tokens"),
                ),
                (
                    "total_tokens",
                    models.IntegerField(blank=True, null=True, verbose_name="total tokens"),
                ),
                (
                    "estimated_cost_usd",
                    models.DecimalField(
                        blank=True,
                        decimal_places=6,
                        max_digits=10,
                        null=True,
                        verbose_name="estimated cost (USD)",
                    ),
                ),
                (
                    "duration_ms",
                    models.IntegerField(blank=True, null=True, verbose_name="duration (ms)"),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ok", "OK"),
                            ("error", "Error"),
                            ("rate_limited", "Rate limited"),
                        ],
                        default="ok",
                        max_length=20,
                        verbose_name="status",
                    ),
                ),
                ("error_type", models.CharField(blank=True, max_length=80, verbose_name="error type")),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ai_usage_records",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="user",
                    ),
                ),
            ],
            options={
                "verbose_name": "AI usage record",
                "verbose_name_plural": "AI usage records",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="aiusagerecord",
            index=models.Index(fields=["created_at"], name="ai_services_created_2e0f6f_idx"),
        ),
        migrations.AddIndex(
            model_name="aiusagerecord",
            index=models.Index(
                fields=["user", "created_at"], name="ai_services_user_id_9b1a3c_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="aiusagerecord",
            index=models.Index(fields=["operation"], name="ai_services_operati_4d7e21_idx"),
        ),
        migrations.AddIndex(
            model_name="aiusagerecord",
            index=models.Index(
                fields=["provider", "model"], name="ai_services_provide_a3f8b2_idx"
            ),
        ),
    ]
