"""
City-parameterized seeding engine.

`create_city_data(city_module, ...)` seeds one city's demo dataset from a
data module under data/cities/ (CITY, PARISHES, ITEMS, ROUTES). Platform
taxonomies, demo users and review checklists stay global and idempotent.
Extracted from the legacy scripts/seed_heritage.py (now a thin delegator).
"""

import os
import sys
import time
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


# --- Pedagogical seeding helpers -------------------------------------------
# Give seeded LOM a realistic, *varied* educational layer so that /learn's
# difficulty / context / age filters return meaningful buckets rather than a
# uniform "medium / other". Everything is derived deterministically from the
# item title so re-seeding is reproducible (no random import needed).

_SEED_DIFFICULTIES = ["very_easy", "easy", "medium", "difficult", "very_difficult"]
_SEED_CONTEXTS = ["school", "higher_education", "training", "school", "higher_education"]
_SEED_AGE_RANGES = ["7-9", "10-12", "12-14", "15-17", "18+"]
_SEED_TIMES = ["PT20M", "PT30M", "PT45M", "PT1H", "PT1H30M"]
_SEED_APPROACHES = ["expository", "inquiry", "constructivist", "project_based", "collaborative"]


def _pedagogical_profile(item, *, city_name="Riobamba", country_name="Ecuador"):
    """Return a dict of pedagogical LOM fields varied by the item's title.

    Deterministic: the same title always yields the same profile.
    """
    bucket = sum(ord(c) for c in (item.title or "")) % 5

    category = getattr(getattr(item, "heritage_category", None), "name", None) or "Patrimonio"
    period = getattr(item, "historical_period", "") or ""

    return {
        "difficulty": _SEED_DIFFICULTIES[bucket],
        "context": _SEED_CONTEXTS[bucket],
        "typical_age_range": _SEED_AGE_RANGES[bucket],
        "typical_learning_time": _SEED_TIMES[bucket],
        "pedagogical_approach": _SEED_APPROACHES[bucket],
        "learning_objectives": [
            f"Identificar los rasgos principales de «{item.title}».",
            f"Situar «{item.title}» en su contexto histórico y cultural en {city_name}.",
            f"Valorar la importancia de {category.lower()} en el patrimonio local.",
        ],
        "prerequisites": f"Nociones básicas de historia local de {city_name} y de {country_name}.",
        "competencies": (
            "Análisis del patrimonio cultural; contextualización histórica; "
            "pensamiento crítico sobre la memoria colectiva."
        ),
        "curriculum_alignment": (
            f"Estudios Sociales — Patrimonio y cultura ({category}"
            + (f", {period}" if period else "")
            + ")"
        ),
        "suggested_activities": (
            f"Visita guiada o virtual a «{item.title}»; debate en aula sobre su "
            "conservación; elaboración de una ficha patrimonial por el estudiantado."
        ),
    }

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

def create_city_data(city_module, *, download_remote_media: bool = True):
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

    def download_image(url, timeout=15):
        if not download_remote_media:
            return None
        if requests is None:
            print("`requests` is not installed; skipping remote media downloads.")
            return None
        try:
            print(f"Downloading image from {url}...")
            # Wikimedia (where the city datasets point) rejects the default
            # python-requests User-Agent with 403 — send a descriptive one.
            response = requests.get(
                url,
                timeout=timeout,
                headers={
                    'User-Agent': (
                        'HeritagePlatformSeeder/1.0 '
                        '(participatory heritage platform; demo-data seeding)'
                    )
                },
            )
            if response.status_code == 200:
                # Be polite to Wikimedia between sequential downloads — burst
                # requests from one IP get 429-throttled quickly.
                time.sleep(2)
                return ContentFile(response.content)
            print(f"Download failed ({response.status_code}) for {url}")
        except Exception as e:
            print(f"Failed to download image: {e}")
        return None

    # --- City (from the data module) -----------------------------------------
    from apps.cities.models import City, CityRole

    city_def = dict(city_module.CITY)
    city_slug = city_def.pop("slug")
    lng, lat = city_def.pop("center")
    hero_image_url = city_def.pop("hero_image_url", None)  # not a model field
    city, _ = City.objects.get_or_create(
        slug=city_slug,
        defaults={**city_def, "center": Point(lng, lat, srid=4326)},
    )
    # Branding fill-in for pre-existing rows (get_or_create only applies
    # defaults on creation): set only fields that are still blank, so a
    # re-seed populates branding without clobbering admin edits.
    branding_dirty = False
    for field in ("brand_color", "description", "description_en"):
        value = city_def.get(field)
        if value and not getattr(city, field, ""):
            setattr(city, field, value)
            branding_dirty = True
    # Branding is best-effort, and the backend entrypoint re-runs this seeder
    # on every container start — a failed download leaves hero_image blank, so
    # the attempt repeats on every boot ahead of gunicorn binding. Keep that
    # worst case short rather than paying the full media timeout each time.
    if hero_image_url and not city.hero_image:
        hero_content = download_image(hero_image_url, timeout=5)
        if hero_content:
            city.hero_image.save(f"{city_slug}_hero.jpg", hero_content, save=False)
            branding_dirty = True
    if branding_dirty:
        city.save()
    # Demo per-city governance: the seeded test curator moderates this city.
    CityRole.objects.get_or_create(
        user=test_curator_user, city=city, role=CityRole.ROLE_CURATOR
    )
    print(f"City: {city.name} ({city.slug})")

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

    # 3. Parishes (from the data module)
    parishes_objs = {}
    for p in city_module.PARISHES:
        obj, _ = Parish.objects.get_or_create(name=p["name"], city=city, defaults=p)
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

    items_data = list(city_module.ITEMS)

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
            city=city,
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

        # Create LOM Data. Coverage (LOM 1.6) is the geographic region the
        # learning object applies to — derive it from the city being seeded,
        # not a hardcoded founding-city string.
        lom_coverage = f"{city.name}, {city.country_name}"
        if item_data.get("lom"):
            lom_general = LOMGeneral.objects.create(
                heritage_item=item, title=item.title, description=item.description, language='es',
                coverage=lom_coverage, structure="atomic", aggregation_level=1
            )
            lifecycle = LOMLifeCycle.objects.create(lom_general=lom_general, version="1.0", status="final")
            LOMContributor.objects.create(lifecycle=lifecycle, role="author", entity=user.username, date=date.today())
            LOMRights.objects.create(lom_general=lom_general, cost=False, copyright_and_other_restrictions=True, description="CC BY 4.0")

            # Derive varied, realistic pedagogical metadata so /learn filters
            # (difficulty, context, age, objectives) have something to bite on
            # instead of everything being "medium/other". Deterministic by title
            # so reseeding is reproducible.
            ped = _pedagogical_profile(item, city_name=city.name, country_name=city.country_name)

            edu_data = item_data["lom"].get("educational")
            if edu_data:
                LOMEducational.objects.create(
                    lom_general=lom_general, interactivity_type="expositive",
                    learning_resource_type=edu_data["learning_resource_type"],
                    interactivity_level="medium", semantic_density="medium",
                    intended_end_user_role=edu_data["intended_end_user_role"],
                    context=edu_data["context"], typical_age_range=edu_data["typical_age_range"],
                    difficulty=edu_data["difficulty"], typical_learning_time=edu_data.get("typical_learning_time", "PT1H"),
                    description=f"Recurso educativo para {item.title}", language="es",
                    learning_objectives=ped["learning_objectives"],
                    prerequisites=ped["prerequisites"],
                    competencies=ped["competencies"],
                    pedagogical_approach=ped["pedagogical_approach"],
                    curriculum_alignment=ped["curriculum_alignment"],
                    suggested_activities=ped["suggested_activities"],
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
                coverage=lom_coverage, structure="atomic", aggregation_level=1
            )
             ped = _pedagogical_profile(item, city_name=city.name, country_name=city.country_name)
             LOMEducational.objects.create(
                lom_general=lom_general, learning_resource_type="narrative_text",
                intended_end_user_role="learner", context=ped["context"], typical_age_range=ped["typical_age_range"],
                difficulty=ped["difficulty"], typical_learning_time=ped["typical_learning_time"],
                description="Información General", language="es",
                learning_objectives=ped["learning_objectives"],
                prerequisites=ped["prerequisites"],
                competencies=ped["competencies"],
                pedagogical_approach=ped["pedagogical_approach"],
                curriculum_alignment=ped["curriculum_alignment"],
                suggested_activities=ped["suggested_activities"],
             )

    print(f"Created {len(items_data)} Heritage Items with LOM metadata.")

    # 6. Heritage Routes (declared in the city data module)
    for route_def in list(getattr(city_module, "ROUTES", [])):
        route_def = dict(route_def)
        item_titles = route_def.pop("item_titles", [])
        stop_instructions = route_def.pop("stop_instructions", "")
        stop_minutes = route_def.pop("stop_minutes", 20)

        stop_items, points = [], []
        for title in item_titles:
            item = HeritageItem.objects.filter(title=title, city=city).first()
            if item:
                stop_items.append(item)
                points.append(item.location)
        if len(stop_items) < 2:
            continue

        route = HeritageRoute.objects.create(
            city=city,
            status="published",
            creator=user,
            curator=user,
            path=LineString(points, srid=4326),
            is_official=True,
            **route_def,
        )
        for idx, item in enumerate(stop_items):
            RouteStop.objects.create(
                route=route,
                heritage_item=item,
                order=idx + 1,
                arrival_instructions=stop_instructions.format(title=item.title),
                suggested_time=timedelta(minutes=stop_minutes),
            )
        print(f"Created Route: {route.title}")
