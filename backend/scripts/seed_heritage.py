import os
import sys
from django.contrib.gis.geos import Point, LineString
from django.core.files.base import ContentFile
from django.db import transaction
import base64
from datetime import date, timedelta
try:
    import requests
except ModuleNotFoundError:  # pragma: no cover
    requests = None

def ensure_django(settings_module: str = "config.settings.development") -> None:
    """
    Allow this file to be used both as a standalone script and from inside
    a Django context (e.g., a management command).
    """
    from django.conf import settings

    if settings.configured:
        return

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.append(project_root)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

    import django

    django.setup()

def clean_database():
    ensure_django()
    from apps.education.models import (
        EducationalResource,
        ResourceType,
        ResourceCategory,
        LOMGeneral,
        LOMLifeCycle,
        LOMEducational,
        LOMRights,
        LOMContributor,
        LOMClassification,
    )
    from apps.heritage.models import (
        HeritageCategory,
        HeritageType,
        Parish,
        HeritageItem,
        HeritageRelation,
        MediaFile,
    )
    from apps.moderation.models import (
        ReviewChecklist,
        ReviewChecklistItem,
        ReviewChecklistResponse,
        QualityScore,
        ContributionFlag,
        ContributionVersion,
        CuratorNote,
    )
    from apps.routes.models import (
        HeritageRoute,
        RouteStop,
        UserRouteProgress,
        RouteRating,
    )

    print("Cleaning database...")
    # Delete in reverse order of dependencies
    with transaction.atomic():
        EducationalResource.objects.all().delete()
        ResourceType.objects.all().delete()
        ResourceCategory.objects.all().delete()
        
        # Routes
        RouteRating.objects.all().delete()
        UserRouteProgress.objects.all().delete()
        RouteStop.objects.all().delete()
        HeritageRoute.objects.all().delete()

        # Moderation
        ContributionVersion.objects.all().delete()
        ContributionFlag.objects.all().delete()
        QualityScore.objects.all().delete()
        ReviewChecklistResponse.objects.all().delete()
        ReviewChecklistItem.objects.all().delete()
        ReviewChecklist.objects.all().delete()
        CuratorNote.objects.all().delete()

        LOMClassification.objects.all().delete()
        LOMRights.objects.all().delete()
        LOMEducational.objects.all().delete()
        LOMContributor.objects.all().delete()
        LOMLifeCycle.objects.all().delete()
        LOMGeneral.objects.all().delete()
        
        HeritageRelation.objects.all().delete()
        HeritageItem.objects.all().delete()
        MediaFile.objects.all().delete()
        
        Parish.objects.all().delete()
        HeritageCategory.objects.all().delete()
        HeritageType.objects.all().delete()
    
    print("Database cleaned.")

def create_initial_data(*, download_remote_media: bool = True):
    ensure_django()
    from django.contrib.auth import get_user_model

    from apps.education.models import (
        LOMGeneral,
        LOMLifeCycle,
        LOMEducational,
        LOMRights,
        LOMContributor,
        LOMClassification,
        EducationalResource,
        ResourceType,
        ResourceCategory,
    )
    from apps.heritage.models import (
        HeritageCategory,
        HeritageType,
        Parish,
        HeritageItem,
        HeritageRelation,
        MediaFile,
    )
    from apps.moderation.models import (
        ReviewChecklist,
        ReviewChecklistItem,
        ReviewChecklistResponse,
        QualityScore,
        ContributionFlag,
        ContributionVersion,
        CuratorNote,
    )
    from apps.routes.models import HeritageRoute, RouteStop
    from apps.users.models import UserRole, UserProfile

    User = get_user_model()

    print("Creating initial data...")
    
    # Create Roles
    curator_role, _ = UserRole.objects.get_or_create(name='Curator', slug='curator')
    contributor_role, _ = UserRole.objects.get_or_create(name='Contributor', slug='contributor')
    
    # Use the same admin identity Docker creates (so we don't collide on username/email).
    admin_email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
    admin_username = os.environ.get("DJANGO_SUPERUSER_USERNAME") or admin_email.split("@", 1)[0]
    admin_password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "admin1234")

    user, created = User.objects.update_or_create(
        username=admin_username,
        defaults={
            "email": admin_email,
            "is_staff": True,
            "is_superuser": True,
        },
    )
    if created:
        user.set_password(admin_password)
        user.save()
    
    # Create Admin Profile
    if not hasattr(user, 'profile'):
        UserProfile.objects.create(user=user, role=curator_role, display_name="Admin Curator")

    # Create test user
    # Create test contributor (a@a.com)
    test_contributor_user, created_contrib = User.objects.update_or_create(
        email="a@a.com",
        defaults={
            "username": "test_contributor",
            "first_name": "a",
            "is_staff": False,
            "is_superuser": False
        }
    )
    if created_contrib:
        test_contributor_user.set_password("a")
        test_contributor_user.save()

    UserProfile.objects.update_or_create(
        user=test_contributor_user,
        defaults={'role': contributor_role, 'display_name': "Test Contributor"}
    )

    # Create test curator (b@b.com)
    test_curator_user, created_curator = User.objects.update_or_create(
        email="b@b.com",
        defaults={
            "username": "test_curator",
            "first_name": "b",
            "is_staff": True,
            "is_superuser": False
        }
    )
    if created_curator:
        test_curator_user.set_password("b")
        test_curator_user.save()

    UserProfile.objects.update_or_create(
        user=test_curator_user,
        defaults={'role': curator_role, 'display_name': "Test Curator"}
    )

    # Maintain backward compatibility for script usage
    test_user = test_contributor_user

    # 1. Heritage Types
    types = [
        {"name": "Tangible", "slug": "tangible", "description": "Artefactos físicos, arquitectura y sitios."},
        {"name": "Intangible", "slug": "intangible", "description": "Tradiciones, historia oral, habilidades y conocimiento."},
    ]
    heritage_types = {}
    for t in types:
        obj, _ = HeritageType.objects.get_or_create(slug=t["slug"], defaults=t)
        heritage_types[t["slug"]] = obj

    # 2. Heritage Categories
    categories = [
        {"name": "Arquitectura", "slug": "architecture", "order": 1, "icon": "building"},
        {"name": "Arqueología", "slug": "archaeology", "order": 2, "icon": "archaeology"},
        {"name": "Gastronomía", "slug": "gastronomy", "order": 3, "icon": "utensils"},
        {"name": "Música y Danza", "slug": "music-dance", "order": 4, "icon": "music"},
        {"name": "Tradiciones Orales", "slug": "oral-traditions", "order": 5, "icon": "comments"},
        {"name": "Festividades", "slug": "festivities", "order": 6, "icon": "calendar-star"},
    ]
    heritage_categories = {}
    for c in categories:
        obj, _ = HeritageCategory.objects.get_or_create(slug=c["slug"], defaults=c)
        heritage_categories[c["slug"]] = obj

    # 3. Parishes (Riobamba)
    parishes_data = [
        {"name": "Lizarzaburu", "canton": "Riobamba"},
        {"name": "Maldonado", "canton": "Riobamba"},
        {"name": "Velasco", "canton": "Riobamba"},
        {"name": "Veloz", "canton": "Riobamba"},
        {"name": "Yaruquies", "canton": "Riobamba"},
        {"name": "Cacha", "canton": "Riobamba"},
        {"name": "Calpi", "canton": "Riobamba"},
        {"name": "Cubijíes", "canton": "Riobamba"},
        {"name": "Flores", "canton": "Riobamba"},
        {"name": "Licán", "canton": "Riobamba"},
        {"name": "Licto", "canton": "Riobamba"},
        {"name": "Pungalá", "canton": "Riobamba"},
        {"name": "Punín", "canton": "Riobamba"},
        {"name": "Quimiag", "canton": "Riobamba"},
        {"name": "San Juan", "canton": "Riobamba"},
        {"name": "San Luis", "canton": "Riobamba"},
    ]
    parishes_objs = {}
    for p in parishes_data:
        obj, _ = Parish.objects.get_or_create(name=p["name"], defaults=p)
        parishes_objs[p["name"]] = obj

    # 4. Heritage Items with LOM Data
    checklist, _ = ReviewChecklist.objects.get_or_create(
        name="Revisión Estándar",
        description="Validación estándar para todos los elementos patrimoniales"
    )
    checklist_items_text = [
        "¿El título describe claramente el elemento?",
        "¿La ubicación es precisa y verificada?",
        "¿Las imágenes son de alta resolución y relevantes?",
        "¿La descripción es original y detallada?"
    ]
    checklist_items = []
    for idx, text in enumerate(checklist_items_text):
        item, _ = ReviewChecklistItem.objects.get_or_create(checklist=checklist, text=text, order=idx)
        checklist_items.append(item)

    items_data = [
        # --- PUBLISHED ITEMS ---
        {
            "title": "Catedral de Riobamba",
            "description": "Catedral histórica distinguida por su fachada barroca reconstruida de las ruinas de la antigua Riobamba destruida por el terremoto de 1797. Combina elementos arquitectónicos indígenas y españoles.",
            "location": Point(-78.6575, -1.6732),
            "address": "5 de Junio y Veloz",
            "parish": "Veloz",
            "heritage_type": "tangible",
            "heritage_category": "architecture",
            "historical_period": "colonial",
            "status": "published",
            "media": [
                {"type": "image", "url": "https://upload.wikimedia.org/wikipedia/commons/2/29/Catedral_de_Riobamba%2C_Interior.jpg"},
            ],
            "moderation": {
                "score": {"completeness": 35, "accuracy": 28, "media": 25, "notes": "Excelente detalle."},
                "checklist": True,
                "history": [
                    {"action": "submit", "by": "contributor"},
                    {"action": "approve", "by": "curator", "summary": "Aprobado"}
                ]
            },
           "lom": {
                "educational": {
                    "learning_resource_type": "figure", 
                    "intended_end_user_role": "learner",
                    "context": "school",
                    "typical_age_range": "10-18",
                    "difficulty": "medium",
                    "typical_learning_time": "PT1H"
                }
            }
        },
        {
            "title": "Parque Maldonado",
            "description": "La plaza principal de Riobamba, nombrada en honor al científico Pedro Vicente Maldonado. Sirve como punto de encuentro central y alberga diversas actividades cívicas.",
            "location": Point(-78.6570, -1.6730),
            "address": "Primera Constituyente y Espejo",
            "parish": "Maldonado",
            "heritage_type": "tangible",
            "heritage_category": "architecture",
            "historical_period": "republican",
            "status": "published",
            "media": [
                {"type": "image", "url": "https://upload.wikimedia.org/wikipedia/commons/d/da/01_Catedral_de_San_Pedro_-_Riobamba_%28Chimborazo%29.jpg"}
            ],
             "moderation": {
                "score": {"completeness": 30, "accuracy": 25, "media": 20, "notes": "Buena contribución."},
                "checklist": True,
                "history": [{"action": "submit", "by": "contributor"}, {"action": "approve", "by": "curator"}]
            },
            "lom": {
                "educational": {
                    "learning_resource_type": "narrative_text",
                    "intended_end_user_role": "learner",
                    "context": "other",
                    "typical_age_range": "all",
                    "difficulty": "easy",
                    "typical_learning_time": "PT30M"
                }
            }
        },
        {
            "title": "Hornado de Riobamba",
            "description": "Plato tradicional de cerdo asado famoso en la región, servido típicamente con llapingachos, mote y agrio. Representa una parte clave de la identidad gastronómica local.",
            "location": Point(-78.6480, -1.6650),
            "address": "Mercado La Merced",
            "parish": "Lizarzaburu",
            "heritage_type": "intangible",
            "heritage_category": "gastronomy",
            "historical_period": "contemporary",
            "status": "published",
            "media": [],
             "moderation": {
                "score": {"completeness": 38, "accuracy": 29, "media": 28, "notes": "Relevancia cultural destacada."},
                "checklist": True,
                "history": [{"action": "submit", "by": "contributor"}, {"action": "approve", "by": "curator"}]
            },
            "lom": {
                "educational": {
                    "learning_resource_type": "table",
                    "intended_end_user_role": "learner",
                    "context": "school",
                    "typical_age_range": "15+",
                    "difficulty": "medium",
                    "typical_learning_time": "PT2H"
                }
            }
        },
        {
            "title": "Pase del Niño Viajero",
            "description": "Una colorida festividad religiosa celebrada en diciembre y enero, caracterizada por procesiones, personajes tradicionales como el Diablo Huma y música.",
            "location": Point(-78.6540, -1.6710),
            "address": "Calles céntricas de Riobamba",
            "parish": "Velasco",
            "heritage_type": "intangible",
            "heritage_category": "festivities",
            "historical_period": "contemporary",
            "status": "published",
            "media": [],
            "moderation": {
                "score": {"completeness": 32, "accuracy": 28, "media": 20, "notes": "Vibrante e importante."},
                "checklist": True,
                "history": [{"action": "submit", "by": "contributor"}, {"action": "approve", "by": "curator"}]
            },
            "lom": {
                "educational": {
                    "learning_resource_type": "video",
                    "intended_end_user_role": "learner",
                    "context": "other",
                    "typical_age_range": "all",
                    "difficulty": "easy",
                    "typical_learning_time": "PT45M"
                }
            }
        },
        {
            "title": "Teatro León",
            "description": "Un teatro histórico en Riobamba, conocido por su arquitectura neoclásica y significado cultural como centro de las artes.",
            "location": Point(-78.6560, -1.6720),
            "address": "Primera Constituyente y España",
            "parish": "Maldonado",
            "heritage_type": "tangible",
            "heritage_category": "architecture",
            "historical_period": "republican",
            "status": "published",
            "media": [{"type": "image", "url": "https://upload.wikimedia.org/wikipedia/commons/4/4b/Teatro_Le%C3%B3n_%28Riobamba%2C_Ecuador_1920%29.png"}],
            "moderation": {
                "score": {"completeness": 35, "accuracy": 30, "media": 25, "notes": "Valor histórico."},
                "checklist": True,
                "history": [{"action": "submit", "by": "contributor"}, {"action": "approve", "by": "curator"}]
            },
            "lom": {
                "educational": {
                    "learning_resource_type": "figure",
                    "difficulty": "easy",
                    "context": "school",
                    "typical_age_range": "12-18",
                    "intended_end_user_role": "learner"
                }
            }
        },
        {
            "title": "Iglesia de Balbanera",
            "description": "La primera iglesia católica construida en Ecuador (1534), ubicada cerca de la laguna de Colta. Cuenta con una fachada colonial simple con detalles de talla en piedra indígena.",
            "location": Point(-78.7450, -1.7050),
            "address": "Colta, Panamericana Sur",
            "parish": "Cacha", # Approximation
            "heritage_type": "tangible",
            "heritage_category": "architecture",
            "historical_period": "colonial",
            "status": "published",
            "media": [{"type": "image", "url": "https://upload.wikimedia.org/wikipedia/commons/e/e7/Iglesia_de_Balbanera_Ecuador596.jpg"}],
            "moderation": {
                "score": {"completeness": 40, "accuracy": 30, "media": 30, "notes": "Sitio fundacional."},
                "checklist": True,
                "history": [{"action": "submit", "by": "contributor"}, {"action": "approve", "by": "curator"}]
            },
            "lom": {
                 "educational": {
                    "learning_resource_type": "narrative_text",
                    "context": "higher_education",
                    "difficulty": "medium",
                    "typical_age_range": "18+",
                    "intended_end_user_role": "learner",
                }
            }
        },
        {
            "title": "Estación del Ferrocarril",
            "description": "La estación de tren de Riobamba, una parada clave en el ferrocarril transandino. Simboliza la modernización del país a principios del siglo XX.",
            "location": Point(-78.6600, -1.6680),
            "address": "Av. Daniel León Borja",
            "parish": "Lizarzaburu",
            "heritage_type": "tangible",
            "heritage_category": "architecture",
            "historical_period": "republican",
            "status": "published",
            "media": [{"type": "image", "url": "https://upload.wikimedia.org/wikipedia/commons/e/ea/Ecuador_Riobamba_trainstation.JPG"}],
             "moderation": {
                "score": {"completeness": 33, "accuracy": 28, "media": 22, "notes": "Infraestructura clave."},
                "checklist": True,
                "history": [{"action": "submit", "by": "contributor"}, {"action": "approve", "by": "curator"}]
            },
            "lom": {
                "educational": {
                    "learning_resource_type": "figure",
                    "intended_end_user_role": "learner",
                    "context": "other",
                    "typical_age_range": "all",
                    "difficulty": "easy"
                }
            }
        },
        {
            "title": "Museo de las Conceptas",
            "description": "Un museo de arte religioso ubicado en el Convento de la Inmaculada Concepción. Exhibe esculturas, pinturas y ornamentos de la época colonial.",
            "location": Point(-78.6580, -1.6740),
            "address": "Argentinos y Larrea",
            "parish": "Maldonado",
            "heritage_type": "tangible",
            "heritage_category": "architecture",
            "historical_period": "colonial",
            "status": "published",
            "media": [],
             "moderation": {
                "score": {"completeness": 36, "accuracy": 29, "media": 20, "notes": "Colección importante."},
                "checklist": True,
                "history": [{"action": "submit", "by": "contributor"}, {"action": "approve", "by": "curator"}]
            },
            "lom": {
                "educational": {
                    "learning_resource_type": "figure",
                    "intended_end_user_role": "learner",
                    "context": "school",
                    "typical_age_range": "10-18",
                    "difficulty": "medium"
                }
            }
        },
        {
            "title": "Mercado San Francisco",
            "description": "Un mercado bullicioso conocido por su puestos de comida tradicional, que ofrecen platos como hornado y yaguarlocro, y sirve como centro social.",
            "location": Point(-78.6550, -1.6750),
            "address": "10 de Agosto",
            "parish": "Maldonado",
            "heritage_type": "tangible",
            "heritage_category": "gastronomy", 
            "historical_period": "contemporary",
            "status": "published",
            "media": [],
            "moderation": {
                "score": {"completeness": 30, "accuracy": 25, "media": 20, "notes": "Patrimonio vivo."},
                "checklist": True,
                "history": [{"action": "submit", "by": "contributor"}, {"action": "approve", "by": "curator"}]
            },
            "lom": {
                "educational": {
                    "learning_resource_type": "figure",
                    "intended_end_user_role": "learner",
                    "context": "other",
                    "typical_age_range": "all",
                    "difficulty": "easy"
                }
            }
        },
        {
            "title": "Danza de los Curiquingues",
            "description": "Una danza tradicional realizada durante festivales donde los bailarines se visten como el ave curiquingue, imitando sus movimientos para honrar a la naturaleza.",
            "location": Point(-78.6500, -1.6700),
            "address": "Riobamba",
            "parish": "San Luis",
            "heritage_type": "intangible",
            "heritage_category": "music-dance",
            "historical_period": "unknown", 
            "status": "published",
            "media": [],
            "moderation": {
                "score": {"completeness": 34, "accuracy": 28, "media": 25, "notes": "Danza ancestral."},
                "checklist": True,
                "history": [{"action": "submit", "by": "contributor"}, {"action": "approve", "by": "curator"}]
            },
            "lom": {
                "educational": {
                    "learning_resource_type": "video",
                    "context": "school",
                    "difficulty": "easy",
                    "typical_age_range": "6-12",
                    "intended_end_user_role": "learner"
                }
            }
        },
        {
            "title": "Coplas del Carnaval",
            "description": "Versos ingeniosos y rimados cantados durante la temporada de Carnaval en Chimborazo, expresando alegría, sátira social y lazos comunitarios.",
            "location": Point(-78.6500, -1.6700),
            "address": "Provincial",
            "parish": "Yaruquies",
            "heritage_type": "intangible",
            "heritage_category": "oral-traditions",
            "historical_period": "contemporary",
            "status": "published",
            "media": [],
             "moderation": {
                "score": {"completeness": 31, "accuracy": 28, "media": 15, "notes": "Tradición oral."},
                "checklist": True,
                "history": [{"action": "submit", "by": "contributor"}, {"action": "approve", "by": "curator"}]
            },
            "lom": {
                "educational": {
                    "learning_resource_type": "audio",
                    "intended_end_user_role": "learner",
                    "context": "other",
                    "typical_age_range": "all",
                    "difficulty": "easy"
                }
            }
        },
        {
            "title": "Leyenda del Luterano",
            "description": "Una leyenda colonial sobre un hombre misterioso que supuestamente fue llevado por el diablo en Riobamba, reflejando los valores morales de la época.",
            "location": Point(-78.6570, -1.6732),
            "address": "Barrio Santa Rosa",
            "parish": "Veloz",
            "heritage_type": "intangible",
            "heritage_category": "oral-traditions",
            "historical_period": "colonial",
            "status": "published",
            "media": [],
             "moderation": {
                "score": {"completeness": 28, "accuracy": 25, "media": 15, "notes": "Leyenda local."},
                "checklist": True,
                "history": [{"action": "submit", "by": "contributor"}, {"action": "approve", "by": "curator"}]
            },
            "lom": {
                "educational": {
                    "learning_resource_type": "narrative_text",
                    "intended_end_user_role": "learner",
                    "context": "school",
                    "typical_age_range": "10-18",
                    "difficulty": "medium"
                }
            }
        },
        {
            "title": "Chicha Huevona",
            "description": "Una bebida alcohólica tradicional de Riobamba hecha con chicha de jora, huevos, cerveza y azúcar, servida caliente y conocida por sus propiedades energéticas.",
            "location": Point(-78.6500, -1.6700),
            "address": "Riobamba",
            "parish": "Veloz",
            "heritage_type": "intangible",
            "heritage_category": "gastronomy",
            "historical_period": "contemporary",
            "status": "published",
            "media": [],
             "moderation": {
                "score": {"completeness": 35, "accuracy": 30, "media": 20, "notes": "Bebida típica."},
                "checklist": True,
                "history": [{"action": "submit", "by": "contributor"}, {"action": "approve", "by": "curator"}]
            },
            "lom": {
                "educational": {
                    "learning_resource_type": "image",
                    "intended_end_user_role": "learner",
                    "context": "other",
                    "typical_age_range": "all",
                    "difficulty": "easy"
                }
            }
        },
        {
            "title": "Fritada de Cajón",
            "description": "Cerdo frito preparado al estilo tradicional de cajón de madera, típico de la región andina, servido con papas y maíz.",
            "location": Point(-78.6550, -1.6650),
            "address": "Mercados de Riobamba",
            "parish": "Lizarzaburu",
            "heritage_type": "intangible",
            "heritage_category": "gastronomy",
            "historical_period": "contemporary",
            "status": "published",
            "media": [],
             "moderation": {
                "score": {"completeness": 37, "accuracy": 31, "media": 24, "notes": "Deliciosa."},
                "checklist": True,
                "history": [{"action": "submit", "by": "contributor"}, {"action": "approve", "by": "curator"}]
            },
            "lom": {
                "educational": {
                    "learning_resource_type": "image",
                    "intended_end_user_role": "learner",
                    "context": "other",
                    "typical_age_range": "all",
                    "difficulty": "easy"
                }
            }
        },
    ]

    # Paths to sample files relative to PROJECT_ROOT (backend/)
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    SAMPLE_FILES_PATHS = {
        'image': os.path.join(PROJECT_ROOT, 'media/heritage/2025/12/sample_image__png_.png'),
        'audio': os.path.join(PROJECT_ROOT, 'media/heritage/2025/12/sample_audio__mp3_.mp3'),
        'video': os.path.join(PROJECT_ROOT, 'media/heritage/2025/12/sample_video__mp4_.mp4'),
        'document_pdf': os.path.join(PROJECT_ROOT, 'media/heritage/2025/12/sample_pdf_document.pdf'),
        'document_text': os.path.join(PROJECT_ROOT, 'media/heritage/2025/12/sample_text__plain_.txt'),
    }

    dummy_png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
    
    def download_image(url):
        if not download_remote_media:
            return None
        if requests is None:
            print("`requests` is not installed; skipping remote media downloads.")
            return None
        try:
            print(f"Downloading image from {url}...")
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return ContentFile(response.content)
        except Exception as e:
            print(f"Failed to download image: {e}")
        return None

    def get_sample_content(file_type_key):
        """Reads content from local sample files if they exist."""
        path = SAMPLE_FILES_PATHS.get(file_type_key)
        if path and os.path.exists(path):
            try:
                with open(path, 'rb') as f:
                    return f.read(), os.path.basename(path)
            except Exception as e:
                print(f"Error reading sample file {path}: {e}")
        return None, None

    def create_media(type_key, item_title, user, url=None, subtype=None, text_content=None):
        content_file = None
        ext, mime = 'png', 'image/png'
        filename = f"{item_title.lower().replace(' ', '_')}_{type_key}.{ext}"

        # 1. Try URL
        if url:
             content_file = download_image(url)
             if content_file:
                 ext, mime = 'jpg', 'image/jpeg'
                 filename = f"{item_title.lower().replace(' ', '_')}_{type_key}.{ext}"
        
        # 2. Try Sample File (only if no URL)
        if not content_file:
            sample_key = subtype if subtype else type_key
            sample_data, sample_name = get_sample_content(sample_key)
            if sample_data:
                content_file = ContentFile(sample_data)
                filename = sample_name
                # Simple mime inference
                if filename.endswith('.mp3'): mime = 'audio/mpeg'; ext='mp3'
                elif filename.endswith('.mp4'): mime = 'video/mp4'; ext='mp4'
                elif filename.endswith('.pdf'): mime = 'application/pdf'; ext='pdf'
                elif filename.endswith('.txt'): mime = 'text/plain'; ext='txt'
                elif filename.endswith('.png'): mime = 'image/png'; ext='png'

        # 3. Fallback/Dummy generation
        if not content_file:
             if type_key == 'image':
                 content_file = ContentFile(dummy_png)
                 ext, mime = 'png', 'image/png'
             elif type_key == 'audio':
                 content_file = ContentFile(b'ID3\x03\x00\x00\x00\x00\x00\nTIT2\x00\x00\x00\x05\x00\x00\x00Test')
                 ext, mime = 'mp3', 'audio/mpeg'
             elif type_key == 'video':
                 content_file = ContentFile(b'ftypmp42') # Minimal fake mp4 header
                 ext, mime = 'mp4', 'video/mp4'
             elif type_key == 'document':
                 content_file = ContentFile(b'%PDF-1.4\n%EOF')
                 ext, mime = 'pdf', 'application/pdf'
             else:
                 return None
             filename = f"{item_title.lower().replace(' ', '_')}_{type_key}.{ext}"

        if text_content:
             mf = MediaFile(
                file_type=type_key,
                mime_type='text/plain',
                text_content=text_content,
                alt_text=f"{type_key.capitalize()} for {item_title}",
                caption=f"Representative {type_key} for {item_title}",
                uploaded_by=user
            )
             mf.save()
             return mf

        mf = MediaFile(
            file_type=type_key,
            mime_type=mime,
            alt_text=f"{type_key.capitalize()} for {item_title}",
            caption=f"Representative {type_key} for {item_title}",
            uploaded_by=user
        )
        mf.file.save(filename, content_file, save=True)
        return mf

    for item_data in items_data:
        # Create Heritage Item
        item = HeritageItem.objects.create(
            title=item_data["title"],
            description=item_data["description"],
            location=item_data["location"],
            address=item_data["address"],
            parish=parishes_objs.get(item_data["parish"]),
            heritage_type=heritage_types[item_data["heritage_type"]],
            heritage_category=heritage_categories[item_data["heritage_category"]],
            historical_period=item_data["historical_period"],
            status=item_data["status"],
            contributor=test_user,
            curator=user if item_data["status"] in ['published', 'rejected', 'changes_requested'] else None,
            submission_date=date.today(),
            curator_feedback=item_data.get("curator_feedback", "")
        )
        print(f"Created Item: {item.title} [{item.status}]")

        # Add Media
        # Add Media from items_data
        has_image = False
        for media_def in item_data.get("media", []):
            try:
                mf = create_media(media_def["type"], item.title, test_user, media_def.get("url"))
                if mf:
                    if media_def["type"] == 'image': 
                        item.images.add(mf)
                        has_image = True
                    elif media_def["type"] == 'audio': item.audio.add(mf)
                    elif media_def["type"] == 'video': item.video.add(mf)
                    elif media_def["type"] == 'document': item.documents.add(mf)
                item.save()
            except Exception as e:
                print(f"Error media {media_def['type']}: {e}")

        # Add Sample Media based on LOM Type
        lom_data = item_data.get("lom", {})
        edu_data = lom_data.get("educational", {}) if lom_data else {}
        res_type = edu_data.get("learning_resource_type", "unknown")

        should_add_image = res_type in ['figure', 'slide', 'diagram', 'graph', 'image']
        should_add_audio = res_type in ['audio', 'lecture']
        should_add_video = res_type in ['video', 'simulation', 'experiment']
        should_add_doc = res_type in ['report', 'table', 'questionnaire']

        # 1. Image 
        # Always ensure at least one image/thumbnail exists, or if strictly required by type
        if res_type != 'narrative_text':
            if (should_add_image and not has_image) or (not has_image): 
                 # Note: logic here is "If it's a figure, add image. AND if it has no image at all, adds an image".
                 try:
                     mf = create_media('image', item.title, test_user, subtype='image')
                     if mf: item.images.add(mf)
                 except Exception as e: print(f"Error adding sample image: {e}")

        # 2. Audio
        if should_add_audio:
            try:
                 mf = create_media('audio', item.title, test_user, subtype='audio')
                 if mf: item.audio.add(mf)
            except Exception as e: print(f"Error adding sample audio: {e}")

        # 3. Video
        if should_add_video:
            try:
                 mf = create_media('video', item.title, test_user, subtype='video')
                 if mf: item.video.add(mf)
            except Exception as e: print(f"Error adding sample video: {e}")
        
        # 4. Documents (PDF only)
        should_add_doc = res_type in ['report', 'table', 'questionnaire']
        should_add_text = res_type == 'narrative_text'

        # 4. Documents (PDF only)
        if should_add_doc:
            try:
                 mf = create_media('document', item.title, test_user, subtype='document_pdf')
                 if mf: item.documents.add(mf)
            except Exception as e: print(f"Error adding sample pdf: {e}")

        # 5. Narrative Text (Stored as text)
        if should_add_text:
            try:
                 # Generate some dummy narrative text
                 narrative = f"Narrative description for {item.title}.\n\nThis is a detailed text resource that explains the history and significance of {item.title}. It is stored directly in the database as text content, not as a PDF file.\n\nLorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
                 mf = create_media('document', item.title, test_user, subtype='text', text_content=narrative)
                 if mf: item.documents.add(mf)
            except Exception as e: print(f"Error adding sample text: {e}")
        
        item.save()

        # Quality Score
        mod_data = item_data.get("moderation", {})
        if "score" in mod_data:
            s = mod_data["score"]
            QualityScore.objects.create(
                heritage_item=item,
                completeness_score=s["completeness"],
                accuracy_score=s["accuracy"],
                media_quality_score=s["media"],
                total_score=s["completeness"]+s["accuracy"]+s["media"],
                notes=s["notes"],
                scored_by=user
            )

        # Checklist
        if mod_data.get("checklist"):
            for cli in checklist_items:
                ReviewChecklistResponse.objects.create(
                    heritage_item=item,
                    checklist_item=cli,
                    curator=user,
                    is_checked=True,
                    notes="Verificado."
                )
        
        # Curator Notes
        for note in mod_data.get("notes", []):
            CuratorNote.objects.create(heritage_item=item, curator=user, content=note)

        # Flags
        for flag_type in mod_data.get("flags", []):
            ContributionFlag.objects.create(
                heritage_item=item, flagged_by=user, flag_type=flag_type, 
                status='resolved' if item.status=='rejected' else 'open'
            )

        # Version History
        version_counter = 1
        history = mod_data.get("history", [])
        for event in history:
            actor = test_user if event["by"] == "contributor" else user
            actor_type = "contributor" if event["by"] == "contributor" else "curator"
            
            ContributionVersion.objects.create(
                heritage_item=item,
                version_number=version_counter,
                created_by=actor,
                created_by_type=actor_type,
                changes_summary=event.get("summary", "Actualización"),
                data_snapshot={"title": item.title, "status": "simulated"}
            )
            version_counter += 1

        # Create LOM Data
        if item_data.get("lom"):
            lom_general = LOMGeneral.objects.create(
                heritage_item=item, title=item.title, description=item.description, language='es',
                coverage="Riobamba, Ecuador", structure="atomic", aggregation_level=1
            )
            lifecycle = LOMLifeCycle.objects.create(lom_general=lom_general, version="1.0", status="final")
            LOMContributor.objects.create(lifecycle=lifecycle, role="author", entity=user.username, date=date.today())
            LOMRights.objects.create(lom_general=lom_general, cost=False, copyright_and_other_restrictions=True, description="CC BY 4.0")

            edu_data = item_data["lom"].get("educational")
            if edu_data:
                LOMEducational.objects.create(
                    lom_general=lom_general, interactivity_type="expositive",
                    learning_resource_type=edu_data["learning_resource_type"],
                    interactivity_level="medium", semantic_density="medium",
                    intended_end_user_role=edu_data["intended_end_user_role"],
                    context=edu_data["context"], typical_age_range=edu_data["typical_age_range"],
                    difficulty=edu_data["difficulty"], typical_learning_time=edu_data.get("typical_learning_time", "PT1H"),
                    description=f"Recurso educativo para {item.title}", language="es"
                )
            
            class_data = item_data["lom"].get("classification")
            if class_data:
                LOMClassification.objects.create(
                    lom_general=lom_general, purpose=class_data.get("purpose", "discipline"),
                    taxon_source="Local Heritage Taxonomy", taxon_entry=class_data.get("taxon_entry", "")
                )
        else:
             lom_general = LOMGeneral.objects.create(
                heritage_item=item, title=item.title, description=item.description, language='es',
                coverage="Riobamba, Ecuador", structure="atomic", aggregation_level=1
            )
             LOMEducational.objects.create(
                lom_general=lom_general, learning_resource_type="narrative_text",
                intended_end_user_role="learner", context="other", typical_age_range="all",
                difficulty="medium", typical_learning_time="PT1H", description="Información General", language="es"
             )

    print(f"Created {len(items_data)} Heritage Items with LOM metadata.")

    # 6. Heritage Routes
    # Route 1: Historical Center Walk
    hist_items_titles = ["Parque Maldonado", "Catedral de Riobamba", "Teatro León", "Museo de las Conceptas", "Estación del Ferrocarril"]
    hist_items = []
    points = []
    for title in hist_items_titles:
        item = HeritageItem.objects.filter(title=title).first()
        if item:
            hist_items.append(item)
            points.append(item.location)
    
    if len(hist_items) >= 2:
        route1 = HeritageRoute.objects.create(
            title="Paseo del Centro Histórico",
            description="Un recorrido por el corazón arquitectónico e histórico de Riobamba, visitando hitos republicanos y coloniales.",
            theme="Historia y Arquitectura",
            difficulty="easy",
            estimated_duration=timedelta(hours=2),
            distance=1.5, # km appx
            status="published",
            creator=user,
            curator=user,
            path=LineString(points, srid=4326),
            is_official=True,
            best_season="year_round",
            accessibility_notes="La mayoría de las calles están pavimentadas pero algunas aceras son estrechas.",
            wheelchair_accessible=True
        )
        
        for idx, item in enumerate(hist_items):
            RouteStop.objects.create(
                route=route1,
                heritage_item=item,
                order=idx + 1,
                arrival_instructions=f"Camine hacia {item.title}.",
                suggested_time=timedelta(minutes=20)
            )
        print(f"Created Route: {route1.title}")

    # Route 2: Gastronomic Tour
    gastro_items_titles = ["Hornado de Riobamba", "Fritada de Cajón", "Chicha Huevona", "Mercado San Francisco"]
    gastro_items = []
    points_g = []
    for title in gastro_items_titles:
        item = HeritageItem.objects.filter(title=title).first()
        if item:
            gastro_items.append(item)
            points_g.append(item.location)
            
    if len(gastro_items) >= 2:
        route2 = HeritageRoute.objects.create(
            title="Ruta Gastronómica de Riobamba",
            description="Saboree los sabores auténticos de la ciudad, desde el famoso Hornado hasta la tradicional Chicha.",
            theme="Gastronomía",
            difficulty="medium", 
            estimated_duration=timedelta(hours=3),
            distance=2.0,
            status="published",
            creator=user,
            curator=user,
            path=LineString(points_g, srid=4326),
            is_official=True,
            best_season="year_round",
             estimated_cost=15.00,
             cost_notes="Estimado por persona para degustación."
        )
        
        for idx, item in enumerate(gastro_items):
            RouteStop.objects.create(
                route=route2,
                heritage_item=item,
                order=idx + 1,
                arrival_instructions="Siguiente parada para degustar.",
                suggested_time=timedelta(minutes=40)
            )
        print(f"Created Route: {route2.title}")

def seed_data():
    clean_database()
    create_initial_data()
    print("Seeding complete.")

if __name__ == "__main__":
    seed_data()
