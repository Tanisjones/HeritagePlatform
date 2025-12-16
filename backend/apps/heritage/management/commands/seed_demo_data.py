import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import LineString, Point
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.contributions.models import Contribution
from apps.education.models import (
    EducationalResource,
    LOMClassification,
    LOMEducational,
    LOMGeneral,
    LOMLifeCycle,
    LOMContributor,
    LOMRights,
    ResourceCategory,
    ResourceType,
)
from apps.heritage.models import Annotation, HeritageCategory, HeritageItem, HeritageType, Parish
from apps.routes.models import HeritageRoute, RouteStop
from apps.users.models import UserProfile, UserRole


class Command(BaseCommand):
    help = "Seed demo data for composite data objects (heritage, LOM, participatory, routes, education)."

    def handle(self, *args, **options):
        with transaction.atomic():
            self.stdout.write(self.style.MIGRATE_HEADING("Seeding demo data..."))
            users = self._create_users()
            taxonomy = self._create_taxonomy()
            parishes = self._create_parishes()
            heritage_items = self._create_heritage_items(users, taxonomy, parishes)
            self._attach_lom_metadata(heritage_items, users)
            self._create_contributions(users, heritage_items)
            self._create_annotations(users, heritage_items)
            self._create_routes(users, heritage_items)
            self._create_educational_resources(users, heritage_items)
            self.stdout.write(self.style.SUCCESS("Demo data seeding complete."))

    def _create_users(self):
        User = get_user_model()
        roles = {
            "contributor": UserRole.objects.get_or_create(
                slug="contributor",
                defaults={"name": "Contributor", "permissions": {"contribute": True}},
            )[0],
            "moderator": UserRole.objects.get_or_create(
                slug="moderator",
                defaults={"name": "Moderator", "permissions": {"moderate": True}},
            )[0],
            "educator": UserRole.objects.get_or_create(
                slug="educator",
                defaults={"name": "Educator", "permissions": {"educate": True}},
            )[0],
        }

        def make_user(email, role_slug, display_name):
            user, _ = User.objects.get_or_create(email=email, defaults={"username": email})
            if not user.password:
                user.set_password("demo1234")
                user.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.display_name = display_name
            profile.role = roles[role_slug]
            profile.save()
            return user

        return {
            "contributor": make_user("contributor@example.com", "contributor", "Alicia Contributor"),
            "moderator": make_user("moderator@example.com", "moderator", "Mateo Moderator"),
            "educator": make_user("educator@example.com", "educator", "Elena Educator"),
        }

    def _create_taxonomy(self):
        tangible, _ = HeritageType.objects.get_or_create(slug="tangible", defaults={"name": "Tangible"})
        intangible, _ = HeritageType.objects.get_or_create(slug="intangible", defaults={"name": "Intangible"})

        architecture, _ = HeritageCategory.objects.get_or_create(
            slug="arquitectura-religiosa",
            defaults={"name": "Arquitectura Religiosa", "description": "Iglesias y catedrales", "order": 1},
        )
        gastronomy, _ = HeritageCategory.objects.get_or_create(
            slug="gastronomia",
            defaults={"name": "Gastronomía", "description": "Platos típicos y bebidas", "order": 2},
        )
        festivities, _ = HeritageCategory.objects.get_or_create(
            slug="festividades",
            defaults={"name": "Festividades", "description": "Fiestas y tradiciones", "order": 3},
        )
        return {
            "types": {"tangible": tangible, "intangible": intangible},
            "categories": {"architecture": architecture, "gastronomy": gastronomy, "festivities": festivities},
        }

    def _create_parishes(self):
        central, _ = Parish.objects.get_or_create(
            name="Riobamba Centro",
            defaults={"canton": "Riobamba", "province": "Chimborazo"},
        )
        san_luis, _ = Parish.objects.get_or_create(
            name="San Luis",
            defaults={"canton": "Riobamba", "province": "Chimborazo"},
        )
        return {"central": central, "san_luis": san_luis}

    def _create_heritage_items(self, users, taxonomy, parishes):
        contributor = users["contributor"]
        items = []
        seed_data = [
            {
                "title": "Iglesia de San Pedro",
                "description": "Templo colonial con arte religioso y fachada de piedra labrada.",
                "coords": (-78.647, -1.669),
                "category": taxonomy["categories"]["architecture"],
                "type": taxonomy["types"]["tangible"],
                "parish": parishes["central"],
                "period": "colonial",
                "status": "published",
                "address": "Calle Primera y Bolívar",
            },
            {
                "title": "Feria de los Lunes",
                "description": "Tradicional feria gastronómica con hornado, jugos y artesanías locales.",
                "coords": (-78.6405, -1.6731),
                "category": taxonomy["categories"]["gastronomy"],
                "type": taxonomy["types"]["intangible"],
                "parish": parishes["central"],
                "period": "republican",
                "status": "published",
                "address": "Plaza Central",
            },
            {
                "title": "Fiesta de la Chonta",
                "description": "Celebración ancestral con música andina, danzas y rituales comunitarios.",
                "coords": (-78.635, -1.661),
                "category": taxonomy["categories"]["festivities"],
                "type": taxonomy["types"]["intangible"],
                "parish": parishes["san_luis"],
                "period": "contemporary",
                "status": "pending",
                "address": "Parque San Luis",
            },
        ]

        for data in seed_data:
            item, _ = HeritageItem.objects.get_or_create(
                title=data["title"],
                defaults={
                    "description": data["description"],
                    "location": Point(data["coords"][0], data["coords"][1], srid=4326),
                    "address": data["address"],
                    "parish": data["parish"],
                    "heritage_type": data["type"],
                    "heritage_category": data["category"],
                    "historical_period": data["period"],
                    "status": data["status"],
                    "contributor": contributor,
                },
            )
            items.append(item)
        return items

    def _attach_lom_metadata(self, heritage_items, users):
        educator = users["educator"]
        for idx, item in enumerate(heritage_items, start=1):
            lom_general, _ = LOMGeneral.objects.get_or_create(
                heritage_item=item,
                defaults={
                    "title": f"Recurso educativo {idx} - {item.title}",
                    "language": random.choice(["es", "en"]),
                    "description": f"Material pedagógico sobre {item.title}.",
                    "keywords": "patrimonio,educacion,riobamba",
                    "coverage": "Riobamba, Ecuador",
                    "structure": "atomic",
                    "aggregation_level": 2,
                },
            )
            lifecycle, _ = LOMLifeCycle.objects.get_or_create(
                lom_general=lom_general,
                defaults={"version": "1.0", "status": "final"},
            )
            LOMContributor.objects.get_or_create(
                lifecycle=lifecycle,
                role="author",
                entity=educator.email,
            )
            LOMEducational.objects.get_or_create(
                lom_general=lom_general,
                defaults={
                    "interactivity_type": "mixed",
                    "learning_resource_type": random.choice(
                        [
                            "narrative_text",
                            "lecture",
                            "exercise",
                            "problem_statement",
                            "self_assessment",
                        ]
                    ),
                    "interactivity_level": random.choice(["medium", "high"]),
                    "semantic_density": random.choice(["medium", "high"]),
                    "intended_end_user_role": random.choice(["learner", "teacher"]),
                    "context": random.choice(["school", "higher_education", "training"]),
                    "typical_age_range": random.choice(["12-15", "15-18", "18+"]),
                    "difficulty": random.choice(["easy", "medium", "difficult"]),
                    "typical_learning_time": "PT30M",
                    "description": "Actividades y preguntas guiadas.",
                    "language": lom_general.language,
                },
            )
            LOMRights.objects.get_or_create(
                lom_general=lom_general,
                defaults={
                    "cost": False,
                    "copyright_and_other_restrictions": False,
                    "description": "Uso educativo abierto.",
                },
            )
            LOMClassification.objects.get_or_create(
                lom_general=lom_general,
                purpose="discipline",
                taxon_source="local",
                taxon_entry="Patrimonio",
                defaults={"keywords": "cultura, historia"},
            )

    def _create_contributions(self, users, heritage_items):
        if "contributions_contribution" not in connection.introspection.table_names():
            self.stdout.write(self.style.WARNING("Skipping contributions seeding (table missing, run migrations)."))
            return

        contributor = users["contributor"]
        moderator = users["moderator"]
        for item in heritage_items:
            Contribution.objects.get_or_create(
                heritage_item=item,
                contributor=contributor,
                contribution_type="enrichment",
                defaults={
                    "status": "approved",
                    "content": {"notes": f"Enriquecimiento para {item.title}"},
                    "reviewed_at": timezone.now(),
                    "reviewer": moderator,
                },
            )

    def _create_annotations(self, users, heritage_items):
        contributor = users["contributor"]
        educator = users["educator"]
        notes = [
            "Detalle iconográfico relevante.",
            "Potencial para visitas educativas.",
            "Agregar referencias bibliográficas locales.",
        ]
        for item in heritage_items:
            for author in (contributor, educator):
                Annotation.objects.get_or_create(
                    heritage_item=item,
                    user=author,
                    defaults={"content": random.choice(notes)},
                )

    def _create_routes(self, users, heritage_items):
        if "routes_heritageroute" not in connection.introspection.table_names():
            self.stdout.write(self.style.WARNING("Skipping routes seeding (table missing, run migrations)."))
            return

        creator = users["educator"]
        route, _ = HeritageRoute.objects.get_or_create(
            title="Recorrido Centro Histórico",
            defaults={
                "description": "Ruta corta por puntos emblemáticos.",
                "theme": "Historia y cultura",
                "difficulty": "easy",
                "estimated_duration": timedelta(hours=2),
                "distance": 3.5,
                "path": LineString(
                    *[item.location for item in heritage_items],
                    srid=4326,
                ),
                "creator": creator,
                "is_official": True,
                "status": "published",
            },
        )
        for order, item in enumerate(heritage_items, start=1):
            RouteStop.objects.get_or_create(
                route=route,
                heritage_item=item,
                defaults={"order": order, "arrival_instructions": "Punto de interés"},
            )

    def _create_educational_resources(self, users, heritage_items):
        required_tables = {"education_resourcetype", "education_resourcecategory", "education_educationalresource"}
        existing = set(connection.introspection.table_names())
        if not required_tables.issubset(existing):
            self.stdout.write(
                self.style.WARNING(
                    "Skipping educational resources seeding (education tables missing, run migrations)."
                )
            )
            return

        educator = users["educator"]
        resource_type, _ = ResourceType.objects.get_or_create(name="Guía Didáctica", defaults={"slug": "guia"})
        category, _ = ResourceCategory.objects.get_or_create(name="Historia Local", defaults={"slug": "historia-local"})

        for idx, item in enumerate(heritage_items, start=1):
            resource, _ = EducationalResource.objects.get_or_create(
                title=f"Secuencia de aprendizaje {idx} - {item.title}",
                defaults={
                    "description": "Actividades para aula y visita guiada.",
                    "resource_type": resource_type,
                    "category": category,
                    "author": educator,
                    "content": f"<p>Contexto histórico de {item.title} y ejercicios.</p>",
                },
            )
            resource.related_heritage_items.add(item)
