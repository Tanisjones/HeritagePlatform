"""
Tarragona, Catalonia (Spain) — demo dataset for a second, European city.

Consumed by scripts/seed_city_engine.py (via `manage.py seed_city tarragona`).
Structure mirrors data/cities/riobamba.py: CITY / PARISHES / ITEMS / ROUTES.

Tarragona is the Roman *Tarraco* — a UNESCO World Heritage site (1st c. BC)
— so the tangible heritage skews Roman and medieval, while the intangible
layer captures living Catalan traditions (castells, calçotada, Santa Tecla).

NOTE on `historical_period`: the model's choices are Ecuador-centric
(pre-columbian / colonial / republican / contemporary / unknown). European
periods don't map onto them, so ancient/Roman/medieval monuments use
"unknown" and living traditions use "contemporary" — this keeps the data
valid and avoids mislabeling Roman ruins as "Colonial" in the UI.

Media URLs point at Wikimedia Commons Special:FilePath (same convention as
Riobamba); the seeder downloads them with a descriptive User-Agent.
"""

from datetime import timedelta

from django.contrib.gis.geos import Point


CITY = {
    "slug": "tarragona",
    "name": "Tarragona",
    "name_es": "Tarragona",
    "country": "ES",
    "country_name": "Spain",
    "country_name_es": "España",
    "region": "Cataluña",
    "timezone": "Europe/Madrid",
    "center": (1.2445, 41.1189),  # lng, lat — Part Alta / Plaça de la Font
    "default_zoom": 14,
    "default_language": "es",
}

# Tarragona's historic districts and nearby municipalities within the
# archaeological ensemble. "canton" is reused (model field) to hold the comarca.
PARISHES = [
    {"name": "Part Alta", "canton": "Tarragonès"},
    {"name": "Eixample", "canton": "Tarragonès"},
    {"name": "El Serrallo", "canton": "Tarragonès"},
    {"name": "Sant Pere i Sant Pau", "canton": "Tarragonès"},
    {"name": "Nou Eixample", "canton": "Tarragonès"},
    {"name": "Bonavista", "canton": "Tarragonès"},
    {"name": "Torreforta", "canton": "Tarragonès"},
    {"name": "Ferran", "canton": "Tarragonès"},
    {"name": "Constantí", "canton": "Tarragonès"},
    {"name": "Altafulla", "canton": "Tarragonès"},
]

ITEMS = [
    # ------------------------------------------------------------------ #
    # TANGIBLE — Roman Tarraco (UNESCO World Heritage)
    # ------------------------------------------------------------------ #
    {
        "title": "Anfiteatro Romano de Tarragona",
        "description": (
            "Anfiteatro del siglo II d.C. situado junto al mar, donde se "
            "celebraban combates de gladiadores y ejecuciones. Sobre la arena "
            "se conservan los restos de una basílica visigoda y una iglesia "
            "románica que recuerdan el martirio del obispo Fructuoso en el 259 d.C. "
            "Forma parte del conjunto arqueológico de Tárraco, Patrimonio de la "
            "Humanidad por la UNESCO desde el año 2000."
        ),
        "location": Point(1.2570, 41.1150),
        "address": "Parc de l'Amfiteatre, s/n",
        "parish": "Part Alta",
        "heritage_type": "tangible",
        "heritage_category": "archaeology",
        "historical_period": "unknown",  # Roman — see module note
        "status": "published",
        "media": [
            {"type": "image", "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Tarragona_Amphitheatre.jpg"},
        ],
        "moderation": {
            "score": {"completeness": 40, "accuracy": 32, "media": 30, "notes": "Monumento emblemático, documentación excelente."},
            "checklist": True,
            "history": [
                {"action": "submit", "by": "contributor"},
                {"action": "approve", "by": "curator", "summary": "Aprobado — Patrimonio UNESCO"},
            ],
        },
        "lom": {
            "educational": {
                "learning_resource_type": "figure",
                "intended_end_user_role": "learner",
                "context": "school",
                "typical_age_range": "10-18",
                "difficulty": "medium",
                "typical_learning_time": "PT1H",
            }
        },
    },
    {
        "title": "Catedral de Santa María de Tarragona",
        "description": (
            "Catedral construida entre los siglos XII y XIV sobre el antiguo "
            "templo romano de culto imperial. Combina el románico de su cabecera "
            "con el gótico de la nave y la fachada, y conserva un notable claustro "
            "con capiteles esculpidos. Es la seu primada de Cataluña."
        ),
        "location": Point(1.2560, 41.1195),
        "address": "Pla de la Seu, s/n",
        "parish": "Part Alta",
        "heritage_type": "tangible",
        "heritage_category": "architecture",
        "historical_period": "unknown",  # Medieval
        "status": "published",
        "media": [
            {"type": "image", "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Catedral%20de%20Tarragona-55.jpg"},
        ],
        "moderation": {
            "score": {"completeness": 38, "accuracy": 30, "media": 28, "notes": "Joya del gótico catalán."},
            "checklist": True,
            "history": [
                {"action": "submit", "by": "contributor"},
                {"action": "approve", "by": "curator"},
            ],
        },
        "lom": {
            "educational": {
                "learning_resource_type": "figure",
                "intended_end_user_role": "learner",
                "context": "school",
                "typical_age_range": "12-18",
                "difficulty": "medium",
                "typical_learning_time": "PT1H",
            }
        },
    },
    {
        "title": "Acueducto de les Ferreres (Pont del Diable)",
        "description": (
            "Acueducto romano del siglo I d.C. que abastecía de agua a Tárraco "
            "desde el río Francolí. Conocido popularmente como el «Pont del "
            "Diable», conserva dos pisos de arcos con 217 metros de longitud y "
            "27 de altura máxima. Es uno de los acueductos romanos mejor "
            "conservados de la península ibérica."
        ),
        "location": Point(1.2430, 41.1470),
        "address": "N-240, Àrea del Pont del Diable",
        "parish": "Sant Pere i Sant Pau",
        "heritage_type": "tangible",
        "heritage_category": "archaeology",
        "historical_period": "unknown",  # Roman
        "status": "published",
        "media": [
            {"type": "image", "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Les%20Ferreres%20Aqueduct.jpg"},
        ],
        "moderation": {
            "score": {"completeness": 39, "accuracy": 31, "media": 29, "notes": "Ingeniería romana excepcional."},
            "checklist": True,
            "history": [
                {"action": "submit", "by": "contributor"},
                {"action": "approve", "by": "curator"},
            ],
        },
        "lom": {
            "educational": {
                "learning_resource_type": "figure",
                "intended_end_user_role": "learner",
                "context": "school",
                "typical_age_range": "10-18",
                "difficulty": "medium",
                "typical_learning_time": "PT45M",
            }
        },
    },
    {
        "title": "Murallas Romanas de Tarragona",
        "description": (
            "El tramo de muralla romana más antiguo fuera de Italia, iniciado en "
            "el siglo II a.C. El Passeig Arqueològic recorre unos 1.100 metros de "
            "lienzo con torres ciclópeas como la de Minerva y la del Cabiscol. "
            "Delimitaba la parte alta de la ciudad, centro político y religioso "
            "de la provincia Hispania Citerior."
        ),
        "location": Point(1.2585, 41.1210),
        "address": "Passeig Arqueològic, s/n",
        "parish": "Part Alta",
        "heritage_type": "tangible",
        "heritage_category": "archaeology",
        "historical_period": "unknown",  # Roman
        "status": "published",
        "media": [
            {"type": "image", "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Muralla%20romana%2C%20Passeig%20Arqueol%C3%B2gic%2C%2005%2C%20torre.jpg"},
        ],
        "moderation": {
            "score": {"completeness": 36, "accuracy": 30, "media": 26, "notes": "Fortificación fundacional."},
            "checklist": True,
            "history": [
                {"action": "submit", "by": "contributor"},
                {"action": "approve", "by": "curator"},
            ],
        },
        "lom": {
            "educational": {
                "learning_resource_type": "narrative_text",
                "intended_end_user_role": "learner",
                "context": "higher_education",
                "typical_age_range": "18+",
                "difficulty": "medium",
                "typical_learning_time": "PT1H",
            }
        },
    },
    {
        "title": "Balcó del Mediterrani",
        "description": (
            "Mirador situado sobre el mar al final de la Rambla Nova, inaugurado "
            "a finales del siglo XIX. Su barandilla de hierro forjado es objeto de "
            "la tradición de «tocar ferro» para atraer la buena suerte. Ofrece "
            "vistas al puerto, la playa del Miracle y el anfiteatro romano."
        ),
        "location": Point(1.2510, 41.1160),
        "address": "Balcó del Mediterrani, Rambla Nova",
        "parish": "Eixample",
        "heritage_type": "tangible",
        "heritage_category": "architecture",
        "historical_period": "contemporary",
        "status": "published",
        "media": [
            {"type": "image", "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Balc%C3%B3%20del%20Mediterrani%2001.jpg"},
        ],
        "moderation": {
            "score": {"completeness": 30, "accuracy": 26, "media": 22, "notes": "Icono ciudadano."},
            "checklist": True,
            "history": [
                {"action": "submit", "by": "contributor"},
                {"action": "approve", "by": "curator"},
            ],
        },
        "lom": {
            "educational": {
                "learning_resource_type": "image",
                "intended_end_user_role": "learner",
                "context": "other",
                "typical_age_range": "all",
                "difficulty": "easy",
                "typical_learning_time": "PT20M",
            }
        },
    },
    {
        "title": "Circo Romano de Tarragona",
        "description": (
            "Circo del siglo I d.C. donde se celebraban carreras de carros, con "
            "capacidad para unos 30.000 espectadores. Es uno de los mejor "
            "conservados de Occidente: se pueden recorrer las bóvedas subterráneas "
            "y la Torre del Pretori que lo conectaba con el foro provincial."
        ),
        "location": Point(1.2555, 41.1165),
        "address": "Rambla Vella, s/n",
        "parish": "Part Alta",
        "heritage_type": "tangible",
        "heritage_category": "archaeology",
        "historical_period": "unknown",  # Roman
        "status": "published",
        "media": [
            {"type": "image", "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Circ%20Rom%C3%A0%20de%20Tarragona-1.JPG"},
        ],
        "moderation": {
            "score": {"completeness": 37, "accuracy": 31, "media": 27, "notes": "Circo excepcionalmente conservado."},
            "checklist": True,
            "history": [
                {"action": "submit", "by": "contributor"},
                {"action": "approve", "by": "curator"},
            ],
        },
        "lom": {
            "educational": {
                "learning_resource_type": "figure",
                "intended_end_user_role": "learner",
                "context": "school",
                "typical_age_range": "10-18",
                "difficulty": "medium",
                "typical_learning_time": "PT45M",
            }
        },
    },
    {
        "title": "Barrio del Serrallo",
        "description": (
            "Barrio marinero tradicional junto al puerto, corazón de la cultura "
            "pesquera de Tarragona. Sus restaurantes conservan las recetas de la "
            "cocina marinera local y cada mañana se subasta el pescado fresco en "
            "la lonja. Es el origen de platos como el «romesco de peix»."
        ),
        "location": Point(1.2340, 41.1090),
        "address": "Moll de Pescadors, El Serrallo",
        "parish": "El Serrallo",
        "heritage_type": "tangible",
        "heritage_category": "gastronomy",
        "historical_period": "contemporary",
        "status": "published",
        "media": [],
        "moderation": {
            "score": {"completeness": 31, "accuracy": 27, "media": 18, "notes": "Patrimonio marinero vivo."},
            "checklist": True,
            "history": [
                {"action": "submit", "by": "contributor"},
                {"action": "approve", "by": "curator"},
            ],
        },
        "lom": {
            "educational": {
                "learning_resource_type": "figure",
                "intended_end_user_role": "learner",
                "context": "other",
                "typical_age_range": "all",
                "difficulty": "easy",
                "typical_learning_time": "PT30M",
            }
        },
    },
    # ------------------------------------------------------------------ #
    # INTANGIBLE — living Catalan traditions
    # ------------------------------------------------------------------ #
    {
        "title": "Castells (Torres Humanas)",
        "description": (
            "Torres humanas construidas por «colles castelleres» como los Xiquets "
            "de Tarragona, una tradición catalana declarada Patrimonio Cultural "
            "Inmaterial de la Humanidad por la UNESCO en 2010. Los castells se "
            "levantan en fiestas mayores al son de la «gralla» y culminan cuando "
            "el «enxaneta» corona la torre."
        ),
        "location": Point(1.2540, 41.1185),
        "address": "Plaça de la Font",
        "parish": "Part Alta",
        "heritage_type": "intangible",
        "heritage_category": "festivities",
        "historical_period": "contemporary",
        "status": "published",
        "media": [
            {"type": "image", "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Castellers.jpg"},
        ],
        "moderation": {
            "score": {"completeness": 40, "accuracy": 33, "media": 28, "notes": "Patrimonio inmaterial UNESCO."},
            "checklist": True,
            "history": [
                {"action": "submit", "by": "contributor"},
                {"action": "approve", "by": "curator"},
            ],
        },
        "lom": {
            "educational": {
                "learning_resource_type": "video",
                "intended_end_user_role": "learner",
                "context": "school",
                "typical_age_range": "all",
                "difficulty": "easy",
                "typical_learning_time": "PT45M",
            }
        },
    },
    {
        "title": "Fiestas de Santa Tecla",
        "description": (
            "Fiesta mayor de Tarragona, celebrada en torno al 23 de septiembre en "
            "honor a la patrona. Declarada Fiesta de Interés Turístico Nacional, "
            "reúne el «seguici popular» con gigantes, bestiario de fuego, el Ball "
            "de Diables y actuaciones castelleras en la Plaça de la Font."
        ),
        "location": Point(1.2545, 41.1187),
        "address": "Centro histórico (Part Alta)",
        "parish": "Part Alta",
        "heritage_type": "intangible",
        "heritage_category": "festivities",
        "historical_period": "contemporary",
        "status": "published",
        "media": [],
        "moderation": {
            "score": {"completeness": 34, "accuracy": 29, "media": 20, "notes": "Fiesta mayor de la ciudad."},
            "checklist": True,
            "history": [
                {"action": "submit", "by": "contributor"},
                {"action": "approve", "by": "curator"},
            ],
        },
        "lom": {
            "educational": {
                "learning_resource_type": "video",
                "intended_end_user_role": "learner",
                "context": "other",
                "typical_age_range": "all",
                "difficulty": "easy",
                "typical_learning_time": "PT45M",
            }
        },
    },
    {
        "title": "Calçotada",
        "description": (
            "Comida tradicional de invierno originaria del vecino Valls, extendida "
            "por todo el Camp de Tarragona. Los «calçots» (cebollas tiernas) se "
            "asan a la brasa y se comen con salsa romesco. Es un ritual "
            "gastronómico y social que reúne a familias y amigos de enero a abril."
        ),
        "location": Point(1.2460, 41.1175),
        "address": "Camp de Tarragona",
        "parish": "Eixample",
        "heritage_type": "intangible",
        "heritage_category": "gastronomy",
        "historical_period": "contemporary",
        "status": "published",
        "media": [
            {"type": "image", "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Cal%C3%A7ots.jpg"},
        ],
        "moderation": {
            "score": {"completeness": 36, "accuracy": 30, "media": 24, "notes": "Tradición gastronómica identitaria."},
            "checklist": True,
            "history": [
                {"action": "submit", "by": "contributor"},
                {"action": "approve", "by": "curator"},
            ],
        },
        "lom": {
            "educational": {
                "learning_resource_type": "table",
                "intended_end_user_role": "learner",
                "context": "training",
                "typical_age_range": "15+",
                "difficulty": "medium",
                "typical_learning_time": "PT2H",
            }
        },
    },
    {
        "title": "Salsa Romesco",
        "description": (
            "Salsa emblemática de la cocina tarraconense elaborada con ñoras, "
            "tomate, ajo, almendras y avellanas tostadas, aceite y pan. Acompaña "
            "los calçots y el pescado del Serrallo. Cada familia guarda su propia "
            "versión de la receta, transmitida de generación en generación."
        ),
        "location": Point(1.2400, 41.1120),
        "address": "El Serrallo",
        "parish": "El Serrallo",
        "heritage_type": "intangible",
        "heritage_category": "gastronomy",
        "historical_period": "contemporary",
        "status": "published",
        "media": [],
        "moderation": {
            "score": {"completeness": 33, "accuracy": 29, "media": 18, "notes": "Receta patrimonial local."},
            "checklist": True,
            "history": [
                {"action": "submit", "by": "contributor"},
                {"action": "approve", "by": "curator"},
            ],
        },
        "lom": {
            "educational": {
                "learning_resource_type": "table",
                "intended_end_user_role": "learner",
                "context": "training",
                "typical_age_range": "15+",
                "difficulty": "medium",
                "typical_learning_time": "PT1H",
            }
        },
    },
    {
        "title": "Ball de Diables de Tarragona",
        "description": (
            "Manifestación festiva de origen medieval en la que «diablos» danzan "
            "con carretillas de fuego y pirotecnia al ritmo de tambores, "
            "representando la lucha entre el bien y el mal. Es uno de los elementos "
            "centrales del seguici de Santa Tecla y de la cultura popular catalana."
        ),
        "location": Point(1.2548, 41.1183),
        "address": "Part Alta",
        "parish": "Part Alta",
        "heritage_type": "intangible",
        "heritage_category": "music-dance",
        "historical_period": "contemporary",
        "status": "published",
        "media": [],
        "moderation": {
            "score": {"completeness": 32, "accuracy": 28, "media": 20, "notes": "Cultura festiva del fuego."},
            "checklist": True,
            "history": [
                {"action": "submit", "by": "contributor"},
                {"action": "approve", "by": "curator"},
            ],
        },
        "lom": {
            "educational": {
                "learning_resource_type": "video",
                "intended_end_user_role": "learner",
                "context": "school",
                "typical_age_range": "12-18",
                "difficulty": "easy",
                "typical_learning_time": "PT30M",
            }
        },
    },
    {
        "title": "Leyenda de Santa Tecla y el dragón",
        "description": (
            "Tradición oral que narra cómo Santa Tecla, discípula del apóstol "
            "Pablo, protege a la ciudad. Se entrelaza con el bestiario festivo, "
            "en especial el dragón y la Cucafera, criaturas que desfilan en el "
            "seguici popular y forman parte del imaginario colectivo tarraconense."
        ),
        "location": Point(1.2562, 41.1193),
        "address": "Catedral de Tarragona",
        "parish": "Part Alta",
        "heritage_type": "intangible",
        "heritage_category": "oral-traditions",
        "historical_period": "unknown",
        "status": "published",
        "media": [],
        "moderation": {
            "score": {"completeness": 29, "accuracy": 26, "media": 15, "notes": "Tradición oral y bestiario."},
            "checklist": True,
            "history": [
                {"action": "submit", "by": "contributor"},
                {"action": "approve", "by": "curator"},
            ],
        },
        "lom": {
            "educational": {
                "learning_resource_type": "narrative_text",
                "intended_end_user_role": "learner",
                "context": "school",
                "typical_age_range": "10-18",
                "difficulty": "medium",
                "typical_learning_time": "PT30M",
            }
        },
    },
]

ROUTES = [
    {
        "title": "Ruta de la Tárraco Romana",
        "description": (
            "Un recorrido por los grandes monumentos de la antigua Tárraco, "
            "capital de la Hispania Citerior y Patrimonio de la Humanidad, desde "
            "las murallas ciclópeas hasta el anfiteatro junto al mar."
        ),
        "theme": "Historia y Arqueología",
        "difficulty": "easy",
        "estimated_duration": timedelta(hours=3),
        "distance": 2.5,
        "best_season": "spring",
        "accessibility_notes": (
            "El casco antiguo tiene calles empedradas y algunas pendientes; "
            "ciertos yacimientos tienen accesos irregulares."
        ),
        "wheelchair_accessible": False,
        "item_titles": [
            "Murallas Romanas de Tarragona",
            "Circo Romano de Tarragona",
            "Anfiteatro Romano de Tarragona",
            "Catedral de Santa María de Tarragona",
        ],
        "stop_instructions": "Diríjase hacia {title}.",
        "stop_minutes": 30,
    },
    {
        "title": "Ruta Gastronómica del Serrallo",
        "description": (
            "Descubra los sabores del mar y del Camp de Tarragona, del pescado "
            "fresco del barrio marinero del Serrallo a las tradiciones del "
            "romesco y la calçotada."
        ),
        "theme": "Gastronomía",
        "difficulty": "easy",
        "estimated_duration": timedelta(hours=2, minutes=30),
        "distance": 1.8,
        "best_season": "winter",
        "estimated_cost": 25.00,
        "cost_notes": "Estimado por persona para degustación.",
        "item_titles": [
            "Barrio del Serrallo",
            "Salsa Romesco",
            "Calçotada",
        ],
        "stop_instructions": "Siguiente parada para degustar.",
        "stop_minutes": 45,
    },
]
