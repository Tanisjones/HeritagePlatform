"""Seed a small curated set of Ecuadorian curriculum standards (P.6).

Idempotent (get_or_create by code). A starter set for Estudios Sociales /
Educación Cultural y Artística around cultural heritage — extendable in the admin.
Reversible: deletes exactly the seeded codes.
"""

from django.db import migrations


# code, subject, grade_level, description (es). Codes follow the MinEduc pattern.
SEED_STANDARDS = [
    ("CS.3.1.10", "Estudios Sociales", "Básica media",
     "Reconocer y valorar el patrimonio cultural del entorno local como parte de la identidad."),
    ("CS.4.1.1", "Estudios Sociales", "Básica superior",
     "Analizar la historia de la localidad a partir de su patrimonio material e inmaterial."),
    ("ECA.2.3.4", "Educación Cultural y Artística", "Básica elemental",
     "Explorar manifestaciones culturales y artísticas del patrimonio riobambeño."),
    ("ECA.3.2.6", "Educación Cultural y Artística", "Básica media",
     "Documentar y comunicar expresiones culturales locales mediante distintos lenguajes."),
    ("CN.3.5.1", "Ciencias Naturales", "Básica media",
     "Relacionar el paisaje natural con el patrimonio y su conservación."),
]


def seed(apps, schema_editor):
    Standard = apps.get_model("education", "CurriculumStandard")
    for order, (code, subject, grade, desc) in enumerate(SEED_STANDARDS):
        Standard.objects.get_or_create(
            code=code,
            defaults={
                "subject": subject,
                "grade_level": grade,
                "description": desc,
                "description_es": desc,
                "order": order,
            },
        )


def unseed(apps, schema_editor):
    Standard = apps.get_model("education", "CurriculumStandard")
    Standard.objects.filter(code__in=[c for c, *_ in SEED_STANDARDS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("education", "0010_curriculumstandard_lessonplan_standards_rubric_and_more"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
