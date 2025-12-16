from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from apps.heritage.models import HeritageItem, HeritageType, HeritageCategory, Parish
from apps.users.models import User
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Seeds the database with 10 heritage items from Riobamba'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding Riobamba heritage items...')

        # 1. Ensure Dependencies exist
        # User
        user, _ = User.objects.get_or_create(
            email='admin@heritage.com',
            defaults={
                'username': 'admin_seeder',
                'password': 'password123',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if not user.check_password('password123'):
             user.set_password('password123')
             user.save()

        # Heritage Type
        type_tangible, _ = HeritageType.objects.get_or_create(
            slug='tangible',
            defaults={'name': 'Tangible', 'description': 'Physical heritage'}
        )
        type_intangible, _ = HeritageType.objects.get_or_create(
            slug='intangible',
            defaults={'name': 'Intangible', 'description': 'Non-physical heritage'}
        )

        # Heritage Categories
        cat_religious, _ = HeritageCategory.objects.get_or_create(
            slug='religious-architecture',
            defaults={'name': 'Religious Architecture', 'order': 1}
        )
        cat_civil, _ = HeritageCategory.objects.get_or_create(
            slug='civil-architecture',
            defaults={'name': 'Civil Architecture', 'order': 2}
        )
        cat_public, _ = HeritageCategory.objects.get_or_create(
            slug='public-spaces',
            defaults={'name': 'Public Spaces', 'order': 3}
        )
        cat_gastronomy, _ = HeritageCategory.objects.get_or_create(
            slug='gastronomy',
            defaults={'name': 'Gastronomy', 'order': 4}
        )
        cat_historical, _ = HeritageCategory.objects.get_or_create(
            slug='historical-site',
            defaults={'name': 'Historical Site', 'order': 5}
        )
        cat_festivity, _ = HeritageCategory.objects.get_or_create(
            slug='festivity',
            defaults={'name': 'Festivity', 'order': 6}
        )
        cat_tradition, _ = HeritageCategory.objects.get_or_create(
            slug='oral-tradition',
            defaults={'name': 'Oral Tradition', 'order': 7}
        )
        cat_music, _ = HeritageCategory.objects.get_or_create(
            slug='music',
            defaults={'name': 'Music & Dance', 'order': 8}
        )
        cat_knowledge, _ = HeritageCategory.objects.get_or_create(
            slug='traditional-knowledge',
            defaults={'name': 'Traditional Knowledge', 'order': 9}
        )

        # Parish (Defaulting to Maldonado for Riobamba center)
        parish_maldonado, _ = Parish.objects.get_or_create(
            name='Maldonado',
            canton='Riobamba',
            defaults={'province': 'Chimborazo'}
        )
        parish_veloz, _ = Parish.objects.get_or_create(
            name='Veloz',
            canton='Riobamba',
            defaults={'province': 'Chimborazo'}
        )
        parish_lizarzaburu, _ = Parish.objects.get_or_create(
            name='Lizarzaburu',
            canton='Riobamba',
            defaults={'province': 'Chimborazo'}
        )

        # 2. Define Items
        items_data = [
            {
                'title': 'Catedral de Riobamba',
                'description': 'La Catedral de San Pedro de Riobamba es una joya de la arquitectura religiosa. Su fachada barroca fue rescatada de la antigua Riobamba destruida en el terremoto de 1797.',
                'location': Point(-78.6575, -1.6732),
                'parish': parish_maldonado,
                'heritage_type': type_tangible,
                'heritage_category': cat_religious,
                'historical_period': 'colonial',
                'address': '5 de Junio y Veloz'
            },
            {
                'title': 'Parque Maldonado',
                'description': 'Plaza central de Riobamba, rodeada de edificios patrimoniales como la Catedral, el Municipio y la Gobernación. Es el corazón histórico de la ciudad.',
                'location': Point(-78.6576, -1.6735),
                'parish': parish_maldonado,
                'heritage_type': type_tangible,
                'heritage_category': cat_public,
                'historical_period': 'republican',
                'address': 'Primera Constituyente y Espejo'
            },
            {
                'title': 'Estación del Tren de Riobamba',
                'description': 'Punto neurálgico del ferrocarril trasandino. Desde aquí parte la famosa ruta a la Nariz del Diablo. Edificio histórico de gran importancia comercial y turística.',
                'location': Point(-78.6550, -1.6660),
                'parish': parish_lizarzaburu,
                'heritage_type': type_tangible,
                'heritage_category': cat_civil,
                'historical_period': 'republican',
                'address': 'Av. Daniel León Borja y Carabobo'
            },
            {
                'title': 'Loma de Quito',
                'description': 'Sitio histórico donde se libró la Batalla de Riobamba el 21 de abril de 1822. Ofrece una vista panorámica de la ciudad y alberga la Iglesia de San Antonio.',
                'location': Point(-78.6600, -1.6680),
                'parish': parish_veloz,
                'heritage_type': type_tangible,
                'heritage_category': cat_historical,
                'historical_period': 'republican',
                'address': 'Argentinos y 24 de Mayo'
            },
            {
                'title': 'Teatro León',
                'description': 'Histórico teatro construido en la década de 1920. Ha sido restaurado recientemente y es un símbolo de la cultura riobambeña.',
                'location': Point(-78.6560, -1.6720),
                'parish': parish_maldonado,
                'heritage_type': type_tangible,
                'heritage_category': cat_civil,
                'historical_period': 'republican',
                'address': 'Primera Constituyente y España'
            },
            {
                'title': 'Museo de las Conceptas',
                'description': 'Museo de arte religioso ubicado en el antiguo monasterio de las Madres Conceptas. Alberga una importante colección de esculturas, pinturas y objetos litúrgicos.',
                'location': Point(-78.6580, -1.6740),
                'parish': parish_maldonado,
                'heritage_type': type_tangible,
                'heritage_category': cat_religious,
                'historical_period': 'colonial',
                'address': 'Argentinos y Larrea'
            },
            {
                'title': 'Hornado de La Merced',
                'description': 'Tradición gastronómica emblemática de Riobamba. El mercado de La Merced es famoso por preparar este plato con recetas transmitidas por generaciones.',
                'location': Point(-78.6590, -1.6710),
                'parish': parish_maldonado,
                'heritage_type': type_intangible,
                'heritage_category': cat_gastronomy,
                'historical_period': 'contemporary',
                'address': 'Mercado La Merced'
            },
            {
                'title': 'Edificio del Correo',
                'description': 'Magnífico edificio de arquitectura neoclásica. Ha servido como sede de correos y telégrafos, destacando por su imponente diseño en el centro de la ciudad.',
                'location': Point(-78.6570, -1.6725),
                'parish': parish_maldonado,
                'heritage_type': type_tangible,
                'heritage_category': cat_civil,
                'historical_period': 'republican',
                'address': '10 de Agosto y Espejo'
            },
            {
                'title': 'Parque Sucre',
                'description': 'Espacio público presidido por la estatua de Neptuno. Es un punto de encuentro tradicional y está rodeado de importantes edificios educativos y colegios.',
                'location': Point(-78.6520, -1.6700),
                'parish': parish_lizarzaburu,
                'heritage_type': type_tangible,
                'heritage_category': cat_public,
                'historical_period': 'republican',
                'address': '10 de Agosto y España'
            },
            {
                'title': 'Basílica del Sagrado Corazón de Jesús',
                'description': 'Imponente templo católico de estilo neogótico. Su construcción domina el paisaje del parque La Libertad y es un centro de fe importante.',
                'location': Point(-78.6540, -1.6690),
                'parish': parish_veloz,
                'heritage_type': type_tangible,
                'heritage_category': cat_religious,
                'historical_period': 'republican',
                'address': 'Av. Daniel León Borja'
            },
            # Intangible Heritage Items
            {
                'title': 'Pase del Niño Rey de Reyes',
                'description': 'Una de las manifestaciones religiosas y folclóricas más grandes de Riobamba. Se realiza en enero con danzas tradicionales, personajes como el Diablo Huma y el Curiquingue.',
                'location': Point(-78.6500, -1.6700), # Symbolic location
                'parish': parish_maldonado,
                'heritage_type': type_intangible,
                'heritage_category': cat_festivity,
                'historical_period': 'contemporary',
                'address': 'Calles céntricas de Riobamba'
            },
            {
                'title': 'Música de Banda de Pueblo',
                'description': 'Las bandas de pueblo son esenciales en las festividades de Riobamba, interpretando ritmos como el albazo, el capishca y el sanjuanito, manteniendo viva la identidad sonora.',
                'location': Point(-78.6550, -1.6700), # Symbolic location
                'parish': parish_lizarzaburu,
                'heritage_type': type_intangible,
                'heritage_category': cat_music,
                'historical_period': 'contemporary',
                'address': 'Varios barrios de la ciudad'
            },
            {
                'title': 'Leyenda del Padre Billonaco',
                'description': 'Cuenta la historia del fantasma de un sacerdote que se aparecía en las noches de Riobamba, parte de la rica tradición oral y de leyendas de miedo de la ciudad.',
                'location': Point(-78.6575, -1.6732), # Near Cathedral
                'parish': parish_maldonado,
                'heritage_type': type_intangible,
                'heritage_category': cat_tradition,
                'historical_period': 'colonial',
                'address': 'Centro Histórico'
            },
            {
                'title': 'Elaboración de Helados de Paila',
                'description': 'Técnica tradicional de preparación de helados en paila de bronce con hielo del Chimborazo (históricamente) y frutas locales. Un saber culinario ancestral.',
                'location': Point(-78.6590, -1.6710),
                'parish': parish_maldonado,
                'heritage_type': type_intangible,
                'heritage_category': cat_gastronomy,
                'historical_period': 'contemporary',
                'address': 'Mercado San Francisco y La Merced'
            },
            {
                'title': 'Juego del Cuarenta',
                'description': 'Juego de naipes tradicional practicado especialmente durante las Fiestas de Riobamba. Reúne a familias y amigos y fomenta la convivencia social.',
                'location': Point(-78.6576, -1.6735),
                'parish': parish_maldonado,
                'heritage_type': type_intangible,
                'heritage_category': cat_tradition,
                'historical_period': 'contemporary',
                'address': 'Clubes y hogares de Riobamba'
            },
            {
                'title': 'Danza de los Diablos de Lata',
                'description': 'Personaje tradicional de las fiestas riobambeñas, caracterizado por su máscara de hojalata y su baile peculiar. Representa el sincretismo cultural.',
                'location': Point(-78.6530, -1.6680), # Barrio Santa Rosa area
                'parish': parish_veloz,
                'heritage_type': type_intangible,
                'heritage_category': cat_festivity,
                'historical_period': 'republican',
                'address': 'Barrio Santa Rosa'
            },
            {
                'title': 'Jugo de Sal',
                'description': 'Curiosa bebida tradicional que se consume en los mercados de Riobamba, preparada con huevos, jugo de carne y especias. Un remedio popular para la resaca y el cansancio.',
                'location': Point(-78.6590, -1.6710),
                'parish': parish_maldonado,
                'heritage_type': type_intangible,
                'heritage_category': cat_gastronomy,
                'historical_period': 'contemporary',
                'address': 'Mercado La Merced'
            },
            {
                'title': 'Fiesta del Señor del Buen Suceso',
                'description': 'Celebración religiosa muy importante en Riobamba, con procesiones multitudinarias y actos de fe que congregan a miles de fieles cada año.',
                'location': Point(-78.6580, -1.6740),
                'parish': parish_maldonado,
                'heritage_type': type_intangible,
                'heritage_category': cat_festivity,
                'historical_period': 'republican',
                'address': 'Plaza y Templo de la Concepción'
            },
            {
                'title': 'Artesanía en Tagua',
                'description': 'Habilidad artesanal para tallar figuras y joyas en "marfil vegetal". Aunque la materia prima viene de la costa, Riobamba tiene hábiles artesanos que trabajan este material.',
                'location': Point(-78.6540, -1.6720),
                'parish': parish_lizarzaburu,
                'heritage_type': type_intangible,
                'heritage_category': cat_knowledge,
                'historical_period': 'contemporary',
                'address': 'Talleres artesanales'
            },
            {
                'title': 'El Carnaval de Riobamba',
                'description': 'Fiesta llena de algarabía, con coplas, agua y el tradicional "Jueves de Compadres". Es una celebración que une a la comunidad en torno al juego y la música.',
                'location': Point(-78.6576, -1.6735),
                'parish': parish_maldonado,
                'heritage_type': type_intangible,
                'heritage_category': cat_festivity,
                'historical_period': 'contemporary',
                'address': 'Toda la ciudad'
            }
        ]

        created_count = 0
        for item_data in items_data:
            item, created = HeritageItem.objects.get_or_create(
                title=item_data['title'],
                defaults={
                    'description': item_data['description'],
                    'location': item_data['location'],
                    'parish': item_data['parish'],
                    'heritage_type': item_data['heritage_type'],
                    'heritage_category': item_data['heritage_category'],
                    'historical_period': item_data['historical_period'],
                    'address': item_data['address'],
                    'status': 'published',
                    'contributor': user
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created item: {item.title}'))
            else:
                self.stdout.write(self.style.WARNING(f'Item already exists: {item.title}'))

        self.stdout.write(self.style.SUCCESS(f'Successfully created {created_count} heritage items.'))
