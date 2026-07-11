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
    {"name": "Roda de Berà", "canton": "Tarragonès"},
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
        "location": Point(1.2588, 41.11457),  # Wikidata Q2746482
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
            "score": {"completeness": 40, "accuracy": 30, "media": 30, "notes": "Monumento emblemático, documentación excelente."},
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
        "location": Point(1.25806, 41.11917),  # Wikidata (imperial-cult enclosure)
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
        "location": Point(1.243889, 41.145556),  # Wikidata Q623448
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
            "score": {"completeness": 39, "accuracy": 30, "media": 29, "notes": "Ingeniería romana excepcional."},
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
        "location": Point(1.26026, 41.12028),  # Torre de Minerva NE corner, Wikidata Q137831040
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
        "location": Point(1.25652, 41.11377),  # OSM — seaward end of Rambla Nova
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
        "location": Point(1.25681, 41.1158),  # Wikidata Q2629538
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
            "score": {"completeness": 37, "accuracy": 30, "media": 27, "notes": "Circo excepcionalmente conservado."},
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
        "location": Point(1.24100, 41.10920),  # OSM — Moll de Pescadors quay
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
        "location": Point(1.25506, 41.11708),  # OSM — Plaça de la Font centroid
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
            "score": {"completeness": 40, "accuracy": 30, "media": 28, "notes": "Patrimonio inmaterial UNESCO."},
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
        "location": Point(1.25538, 41.11728),  # Plaça de la Font — seguici / actuacions
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
        "location": Point(1.24054, 41.10925),  # El Serrallo (Sant Pere Apòstol)
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
        "location": Point(1.25478, 41.11738),  # Plaça de la Font — Part Alta
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
        "location": Point(1.25841, 41.11939),  # Catedral de Tarragona
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
    # ================================================================== #
    # SECOND WAVE — expanded Tárraco monumental ensemble + more traditions
    # Coordinates cross-checked against Wikidata P625 / OSM (2026-07).
    # ================================================================== #
    {
        "title": "Pretorio Romano (Torre del Pretorio)",
        "description": (
            "Torre romana del siglo I d.C. que articulaba el foro provincial de "
            "Tárraco y conectaba el recinto de culto con la plaza de "
            "representación y el circo. Reconvertida en residencia real medieval "
            "—de ahí el nombre de «Casa del Rei»—, hoy alberga parte del Museo de "
            "Historia y ofrece desde su terraza una vista completa de la ciudad."
        ),
        "location": Point(1.25801, 41.11654),  # OSM — Torre del Pretori
        "address": "Plaça del Rei, s/n",
        "parish": "Part Alta",
        "heritage_type": "tangible",
        "heritage_category": "archaeology",
        "historical_period": "unknown",  # Roman
        "status": "published",
        "media": [
            {"type": "image", "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Tarragona%20-%20Pretori%20rom%C3%A0%20i%20Torre%20del%20Circ.jpg"},
        ],
        "moderation": {
            "score": {"completeness": 37, "accuracy": 30, "media": 27, "notes": "Pieza clave del foro provincial."},
            "checklist": True,
            "history": [
                {"action": "submit", "by": "contributor"},
                {"action": "approve", "by": "curator", "summary": "Aprobado — conjunto UNESCO"},
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
        "title": "Foro Provincial de Tárraco",
        "description": (
            "Gran complejo monumental (siglos I-II d.C.) desde el que se "
            "administraba la provincia Hispania Citerior Tarraconensis, la mayor "
            "del Imperio Romano. Ocupaba la parte alta de la ciudad e integraba "
            "el recinto de culto imperial, la plaza de representación y el circo. "
            "Sus restos afloran hoy entre el trazado medieval de la Part Alta."
        ),
        "location": Point(1.25809, 41.11684),  # Wikidata — Plaça del Rei core
        "address": "Plaça del Fòrum / Plaça del Rei",
        "parish": "Part Alta",
        "heritage_type": "tangible",
        "heritage_category": "archaeology",
        "historical_period": "unknown",  # Roman
        "status": "published",
        "media": [],
        "moderation": {
            "score": {"completeness": 35, "accuracy": 30, "media": 20, "notes": "Centro administrativo de la provincia."},
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
                "difficulty": "difficult",
                "typical_learning_time": "PT1H",
            }
        },
    },
    {
        "title": "Foro de la Colonia",
        "description": (
            "Foro local de la colonia de Tárraco, situado en la ciudad baja cerca "
            "del puerto. Conserva columnas y basamentos del recinto donde se "
            "concentraba la vida civil, comercial y judicial de los ciudadanos "
            "romanos, en el entorno de las actuales calles Lleida y Cavallers."
        ),
        "location": Point(1.24831, 41.11464),  # Wikidata Q4894543
        "address": "Carrer de Lleida, s/n",
        "parish": "Eixample",
        "heritage_type": "tangible",
        "heritage_category": "archaeology",
        "historical_period": "unknown",  # Roman
        "status": "published",
        "media": [
            {"type": "image", "url": "https://commons.wikimedia.org/wiki/Special:FilePath/F%C3%B2rum%20de%20la%20Col%C3%B2nia%2C%20Tarragona.JPG"},
        ],
        "moderation": {
            "score": {"completeness": 33, "accuracy": 29, "media": 22, "notes": "Foro de la ciudad baja."},
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
                "typical_learning_time": "PT45M",
            }
        },
    },
    {
        "title": "Teatro Romano de Tarragona",
        "description": (
            "Teatro de época augustea (finales del siglo I a.C.) construido junto "
            "al foro de la colonia y el puerto, aprovechando la pendiente natural "
            "para la grada. Aunque muy alterado por construcciones posteriores, "
            "conserva parte de la cávea y del edificio escénico, testimonio de la "
            "vida cultural de la Tárraco romana."
        ),
        "location": Point(1.2494, 41.1128),  # Wikidata Q3079841
        "address": "Carrer de Sant Magí, s/n",
        "parish": "Eixample",
        "heritage_type": "tangible",
        "heritage_category": "archaeology",
        "historical_period": "unknown",  # Roman
        "status": "published",
        "media": [],
        "moderation": {
            "score": {"completeness": 30, "accuracy": 28, "media": 18, "notes": "Teatro augusteo junto al puerto."},
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
                "typical_age_range": "12-18",
                "difficulty": "medium",
                "typical_learning_time": "PT30M",
            }
        },
    },
    {
        "title": "Museo Nacional Arqueológico de Tarragona (MNAT)",
        "description": (
            "Principal museo dedicado a la Tárraco romana, fundado en el siglo XIX. "
            "Custodia mosaicos, esculturas, epigrafía y objetos cotidianos "
            "procedentes del conjunto arqueológico, entre ellos el célebre mosaico "
            "de la Medusa. Su sede se levanta junto al Pretorio, en la Plaça del Rei."
        ),
        "location": Point(1.25853, 41.11669),  # Wikidata Q2478458
        "address": "Plaça del Rei, 5",
        "parish": "Part Alta",
        "heritage_type": "tangible",
        "heritage_category": "architecture",
        "historical_period": "contemporary",
        "status": "published",
        "media": [
            {"type": "image", "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Museu%20Nacional%20Arqueol%C3%B2gic%20de%20Tarragona.JPG"},
        ],
        "moderation": {
            "score": {"completeness": 34, "accuracy": 30, "media": 24, "notes": "Referencia museística de Tárraco."},
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
                "typical_age_range": "all",
                "difficulty": "easy",
                "typical_learning_time": "PT1H30M",
            }
        },
    },
    {
        "title": "Necrópolis Paleocristiana de Tarragona",
        "description": (
            "Uno de los conjuntos funerarios paleocristianos más importantes de "
            "Occidente, en uso entre los siglos III y V d.C. junto al río Francolí. "
            "Reúne sarcófagos, mausoleos y miles de tumbas surgidas en torno al "
            "culto a los mártires locales, y forma parte del conjunto de Tárraco "
            "declarado Patrimonio de la Humanidad."
        ),
        "location": Point(1.23852, 41.11575),  # Wikidata Q2972673
        "address": "Passeig de la Independència, 25",
        "parish": "Eixample",
        "heritage_type": "tangible",
        "heritage_category": "archaeology",
        "historical_period": "unknown",  # Late Roman / Early Christian
        "status": "published",
        "media": [
            {"type": "image", "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Necr%C3%B2polis%20paleocristiana%20de%20Tarragona.JPG"},
        ],
        "moderation": {
            "score": {"completeness": 36, "accuracy": 30, "media": 25, "notes": "Necrópolis paleocristiana excepcional."},
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
                "context": "higher_education",
                "typical_age_range": "15+",
                "difficulty": "difficult",
                "typical_learning_time": "PT1H",
            }
        },
    },
    {
        "title": "Casa Castellarnau",
        "description": (
            "Casa señorial gótica del siglo XV en el corazón de la Part Alta, "
            "ampliada y decorada en épocas posteriores por la familia "
            "Castellarnau. Conserva un patio noble, artesonados y mobiliario de "
            "los siglos XVIII y XIX, y hoy es sala del Museo de Historia de "
            "Tarragona."
        ),
        "location": Point(1.255378, 41.117808),  # Wikidata Q16187692
        "address": "Carrer de Cavallers, 14",
        "parish": "Part Alta",
        "heritage_type": "tangible",
        "heritage_category": "architecture",
        "historical_period": "unknown",  # Medieval
        "status": "published",
        "media": [
            {"type": "image", "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Casa%20Castellarnau%2C%20Tarragona.JPG"},
        ],
        "moderation": {
            "score": {"completeness": 32, "accuracy": 28, "media": 22, "notes": "Casa noble gótica bien conservada."},
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
                "difficulty": "easy",
                "typical_learning_time": "PT30M",
            }
        },
    },
    {
        "title": "Portal del Roser",
        "description": (
            "Puerta monumental abierta en la muralla en el siglo XVIII para "
            "comunicar la ciudad amurallada con el arrabal. Conserva el escudo de "
            "la ciudad y da acceso al Passeig Arqueològic; su nombre proviene de "
            "una antigua capilla dedicada a la Mare de Déu del Roser."
        ),
        "location": Point(1.25479, 41.11854),  # OSM
        "address": "Portal del Roser, Part Alta",
        "parish": "Part Alta",
        "heritage_type": "tangible",
        "heritage_category": "architecture",
        "historical_period": "colonial",  # 18th c.
        "status": "published",
        "media": [],
        "moderation": {
            "score": {"completeness": 28, "accuracy": 25, "media": 16, "notes": "Puerta histórica de la muralla."},
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
        "title": "Cantera Romana del Mèdol",
        "description": (
            "Gran cantera a cielo abierto de la que los romanos extrajeron la "
            "piedra para construir buena parte de Tárraco. Destaca la «agulla del "
            "Mèdol», un pináculo de roca de unos 16 metros dejado en pie como "
            "testigo del nivel original del terreno. Se encuentra junto a la Vía "
            "Augusta, al nordeste de la ciudad."
        ),
        "location": Point(1.339232, 41.138775),  # Wikidata Q3079849
        "address": "Àrea del Mèdol (AP-7)",
        "parish": "Ferran",
        "heritage_type": "tangible",
        "heritage_category": "archaeology",
        "historical_period": "unknown",  # Roman
        "status": "published",
        "media": [
            {"type": "image", "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Pedrera%20del%20M%C3%A8dol.JPG"},
        ],
        "moderation": {
            "score": {"completeness": 31, "accuracy": 28, "media": 23, "notes": "Cantera que abasteció a Tárraco."},
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
                "typical_learning_time": "PT30M",
            }
        },
    },
    {
        "title": "Torre de los Escipiones",
        "description": (
            "Torre funeraria romana del siglo I d.C. situada junto a la antigua "
            "Vía Augusta, a unos seis kilómetros de la ciudad. Sus tres cuerpos de "
            "sillería conservan dos figuras esculpidas identificadas popularmente "
            "—sin fundamento histórico— con los Escipiones. Es un monumento "
            "funerario romano de referencia en la costa mediterránea."
        ),
        "location": Point(1.318856, 41.132017),  # Wikidata Q1505731
        "address": "N-340, Vía Augusta",
        "parish": "Ferran",
        "heritage_type": "tangible",
        "heritage_category": "archaeology",
        "historical_period": "unknown",  # Roman
        "status": "published",
        "media": [
            {"type": "image", "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Torre%20dels%20Escipions.jpg"},
        ],
        "moderation": {
            "score": {"completeness": 33, "accuracy": 30, "media": 25, "notes": "Torre funeraria de la Vía Augusta."},
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
                "typical_learning_time": "PT30M",
            }
        },
    },
    {
        "title": "Arco de Bará",
        "description": (
            "Arco de triunfo romano del siglo I d.C. levantado sobre la Vía "
            "Augusta por disposición testamentaria de Lucius Licinius Sura. De un "
            "solo vano y orden corintio, marcaba un punto significativo del camino "
            "hacia el norte. Se conserva en Roda de Berà, a unos veinte kilómetros "
            "de Tarragona, dentro del conjunto de Tárraco."
        ),
        "location": Point(1.469115, 41.173301),  # Wikidata Q631051
        "address": "N-340, Roda de Berà",
        "parish": "Roda de Berà",
        "heritage_type": "tangible",
        "heritage_category": "archaeology",
        "historical_period": "unknown",  # Roman
        "status": "published",
        "media": [
            {"type": "image", "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Arc%20de%20Ber%C3%A0.jpg"},
        ],
        "moderation": {
            "score": {"completeness": 35, "accuracy": 30, "media": 27, "notes": "Arco triunfal de la Vía Augusta."},
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
                "typical_learning_time": "PT30M",
            }
        },
    },
    {
        "title": "Mausoleo de Centcelles",
        "description": (
            "Conjunto romano de Constantí cuya sala principal, cubierta por una "
            "cúpula, conserva uno de los mosaicos paleocristianos más antiguos y "
            "notables de Europa (siglo IV d.C.), con escenas de caza y pasajes "
            "bíblicos. Se ha interpretado como mausoleo imperial y forma parte del "
            "conjunto arqueológico de Tárraco."
        ),
        "location": Point(1.226134, 41.155781),  # Wikidata Q1053521
        "address": "Camí de Centcelles, Constantí",
        "parish": "Constantí",
        "heritage_type": "tangible",
        "heritage_category": "archaeology",
        "historical_period": "unknown",  # Late Roman
        "status": "published",
        "media": [
            {"type": "image", "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Vil%C2%B7la%20romana%20de%20Centcelles%20-%20c%C3%BApula.JPG"},
        ],
        "moderation": {
            "score": {"completeness": 37, "accuracy": 30, "media": 28, "notes": "Mosaico de cúpula paleocristiano único."},
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
                "context": "higher_education",
                "typical_age_range": "15+",
                "difficulty": "difficult",
                "typical_learning_time": "PT1H",
            }
        },
    },
    {
        "title": "Villa Romana de los Munts",
        "description": (
            "Lujosa villa romana costera de Altafulla, ocupada entre los siglos I "
            "y III d.C. Conserva termas, mosaicos, pinturas murales y un sistema "
            "hidráulico notable, testimonio de la vida aristocrática en el "
            "territorio de Tárraco. Forma parte del conjunto Patrimonio de la "
            "Humanidad."
        ),
        "location": Point(1.385456, 41.135872),  # Wikidata Q9093955
        "address": "Els Munts, Altafulla",
        "parish": "Altafulla",
        "heritage_type": "tangible",
        "heritage_category": "archaeology",
        "historical_period": "unknown",  # Roman
        "status": "published",
        "media": [
            {"type": "image", "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Vil%C2%B7la%20dels%20Munts%2C%20Altafulla.JPG"},
        ],
        "moderation": {
            "score": {"completeness": 34, "accuracy": 30, "media": 24, "notes": "Villa aristocrática con termas y mosaicos."},
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
                "typical_learning_time": "PT45M",
            }
        },
    },
    {
        "title": "Mercado Central de Tarragona",
        "description": (
            "Edificio modernista inaugurado en 1915, obra de Josep Maria Pujol de "
            "Barberà, con estructura de hierro y vidrio. Corazón del comercio de "
            "productos frescos de la ciudad, combina la arquitectura noucentista "
            "con la actividad cotidiana de payeses, pescadores y comerciantes del "
            "Camp de Tarragona."
        ),
        "location": Point(1.24893, 41.11587),  # OSM — Plaça Corsini
        "address": "Plaça Corsini, s/n",
        "parish": "Eixample",
        "heritage_type": "tangible",
        "heritage_category": "architecture",
        "historical_period": "contemporary",
        "status": "published",
        "media": [
            {"type": "image", "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Mercat%20Central%20de%20Tarragona.JPG"},
        ],
        "moderation": {
            "score": {"completeness": 31, "accuracy": 27, "media": 22, "notes": "Mercado modernista en uso."},
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
        "title": "Playa del Miracle",
        "description": (
            "Principal playa urbana de Tarragona, situada al pie del anfiteatro "
            "romano y del centro histórico. Su nombre evoca un milagro atribuido a "
            "los mártires locales. Ha sido lugar de baño, pesca y sociabilidad de "
            "los tarraconenses desde el siglo XIX y conecta la ciudad con su "
            "frente marítimo."
        ),
        "location": Point(1.25633, 41.11225),  # OSM
        "address": "Platja del Miracle, s/n",
        "parish": "Eixample",
        "heritage_type": "tangible",
        "heritage_category": "architecture",
        "historical_period": "contemporary",
        "status": "published",
        "media": [],
        "moderation": {
            "score": {"completeness": 26, "accuracy": 23, "media": 15, "notes": "Frente marítimo histórico."},
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
    # ------------------------------------------------------------------ #
    # INTANGIBLE — more living Catalan traditions
    # ------------------------------------------------------------------ #
    {
        "title": "Gigantes y Bestiario de Tarragona",
        "description": (
            "Conjunto de figuras festivas —gigantes, la Cucafera, el dragón, la "
            "Víbria, el Lleó y los cabezudos— que protagonizan el seguici popular "
            "de Santa Tecla. Cada figura tiene su propio baile y música; el "
            "bestiario, de raíz medieval, encarna el imaginario simbólico de la "
            "ciudad y desfila por la Part Alta."
        ),
        "location": Point(1.25522, 41.11821),  # OSM — Plaça del Pallol (Casa de la Festa)
        "address": "Plaça del Pallol (Casa de la Festa)",
        "parish": "Part Alta",
        "heritage_type": "intangible",
        "heritage_category": "festivities",
        "historical_period": "contemporary",
        "status": "published",
        "media": [],
        "moderation": {
            "score": {"completeness": 32, "accuracy": 28, "media": 18, "notes": "Bestiario festivo de raíz medieval."},
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
                "typical_learning_time": "PT30M",
            }
        },
    },
    {
        "title": "Sardana",
        "description": (
            "Danza tradicional catalana que se baila en corro, cogidos de las "
            "manos, al son de la cobla. Símbolo de cohesión y de identidad "
            "colectiva, se interpreta en plazas y fiestas mayores. En Tarragona "
            "acompaña las celebraciones populares y forma parte del repertorio "
            "cultural compartido de Cataluña."
        ),
        "location": Point(1.2568, 41.11352),  # Balcó del Mediterrani area
        "address": "Rambla Nova / Balcó del Mediterrani",
        "parish": "Eixample",
        "heritage_type": "intangible",
        "heritage_category": "music-dance",
        "historical_period": "contemporary",
        "status": "published",
        "media": [],
        "moderation": {
            "score": {"completeness": 30, "accuracy": 27, "media": 16, "notes": "Danza identitaria catalana."},
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
                "typical_learning_time": "PT30M",
            }
        },
    },
    {
        "title": "Correfoc",
        "description": (
            "Celebración nocturna en la que diablos y bestias de fuego recorren "
            "las calles lanzando chispas con carretillas pirotécnicas, mientras el "
            "público baila bajo la lluvia de fuego. De fuerte arraigo en las "
            "fiestas catalanas, en Tarragona es uno de los momentos culminantes "
            "de Santa Tecla."
        ),
        "location": Point(1.25467, 41.11760),  # Part Alta streets
        "address": "Casco antiguo (Part Alta)",
        "parish": "Part Alta",
        "heritage_type": "intangible",
        "heritage_category": "festivities",
        "historical_period": "contemporary",
        "status": "published",
        "media": [],
        "moderation": {
            "score": {"completeness": 31, "accuracy": 28, "media": 18, "notes": "Fiesta del fuego de gran arraigo."},
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
                "typical_age_range": "15+",
                "difficulty": "easy",
                "typical_learning_time": "PT30M",
            }
        },
    },
    {
        "title": "Cultura del Vermut",
        "description": (
            "Ritual social del aperitivo de mediodía, muy arraigado en el Camp de "
            "Tarragona, donde el vermut elaborado con vinos y hierbas locales se "
            "acompaña de conservas y encurtidos. «Hacer el vermut» es una "
            "costumbre de encuentro que estructura el fin de semana en bares y "
            "bodegas de la ciudad."
        ),
        "location": Point(1.24800, 41.11700),  # central Eixample bars
        "address": "Rambla Nova y entorno",
        "parish": "Eixample",
        "heritage_type": "intangible",
        "heritage_category": "gastronomy",
        "historical_period": "contemporary",
        "status": "published",
        "media": [],
        "moderation": {
            "score": {"completeness": 29, "accuracy": 26, "media": 15, "notes": "Costumbre social del aperitivo."},
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
                "context": "other",
                "typical_age_range": "18+",
                "difficulty": "easy",
                "typical_learning_time": "PT20M",
            }
        },
    },
    {
        "title": "Semana Santa de Tarragona",
        "description": (
            "Conjunto de procesiones de raíz gremial y cofrade que recorren la "
            "ciudad durante la Semana Santa, con pasos, tambores y el "
            "característico «armat» (soldados romanos). Combina la devoción "
            "religiosa con un patrimonio de imaginería, música y vestimenta "
            "transmitido por las cofradías tarraconenses."
        ),
        "location": Point(1.25776, 41.11945),  # Catedral / Part Alta
        "address": "Catedral y casco antiguo",
        "parish": "Part Alta",
        "heritage_type": "intangible",
        "heritage_category": "festivities",
        "historical_period": "contemporary",
        "status": "published",
        "media": [],
        "moderation": {
            "score": {"completeness": 30, "accuracy": 27, "media": 16, "notes": "Procesiones cofrades tradicionales."},
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
                "typical_learning_time": "PT30M",
            }
        },
    },
    {
        "title": "Els Xiquets - Cultura Castellera",
        "description": (
            "Más allá de la torre humana en sí, la cultura castellera abarca los "
            "ensayos semanales, la organización de las «colles», el papel de la "
            "«gralla» y el «timbal», y los valores de esfuerzo, equilibrio y "
            "cooperación. En Tarragona, colles como els Xiquets mantienen viva "
            "esta tradición reconocida por la UNESCO."
        ),
        "location": Point(1.25536, 41.1168),  # Plaça de la Font
        "address": "Local de la colla / Plaça de la Font",
        "parish": "Part Alta",
        "heritage_type": "intangible",
        "heritage_category": "festivities",
        "historical_period": "contemporary",
        "status": "published",
        "media": [],
        "moderation": {
            "score": {"completeness": 33, "accuracy": 29, "media": 17, "notes": "Dimensión social de los castells."},
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
                "typical_age_range": "12-18",
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
    {
        "title": "Ruta del Foro Provincial y la Part Alta",
        "description": (
            "Un paseo por el poder de la Tárraco imperial y su pervivencia "
            "medieval: del recinto de culto y el foro provincial a las torres, "
            "casas nobles y puertas que hoy tejen el casco antiguo de Tarragona."
        ),
        "theme": "Historia y Arqueología",
        "difficulty": "easy",
        "estimated_duration": timedelta(hours=2, minutes=30),
        "distance": 1.6,
        "best_season": "autumn",
        "accessibility_notes": (
            "Recorrido por la Part Alta con calles empedradas y pendientes "
            "suaves; algunos yacimientos tienen accesos con escalones."
        ),
        "wheelchair_accessible": False,
        "item_titles": [
            "Catedral de Santa María de Tarragona",
            "Foro Provincial de Tárraco",
            "Pretorio Romano (Torre del Pretorio)",
            "Museo Nacional Arqueológico de Tarragona (MNAT)",
            "Casa Castellarnau",
            "Portal del Roser",
        ],
        "stop_instructions": "Continúe hacia {title}.",
        "stop_minutes": 25,
    },
    {
        "title": "Ruta de la Tárraco Monumental (afueras)",
        "description": (
            "Los grandes monumentos romanos que se extienden más allá de la "
            "ciudad, a lo largo de la Vía Augusta y el territorio de Tárraco: "
            "canteras, torres funerarias, arcos, villas y el mausoleo de "
            "Centcelles. Un itinerario en vehículo por el paisaje romano del Camp."
        ),
        "theme": "Historia y Arqueología",
        "difficulty": "medium",
        "estimated_duration": timedelta(hours=5),
        "distance": 55.0,
        "best_season": "spring",
        "accessibility_notes": (
            "Itinerario disperso que requiere vehículo; los yacimientos al aire "
            "libre tienen superficies irregulares."
        ),
        "wheelchair_accessible": False,
        "item_titles": [
            "Cantera Romana del Mèdol",
            "Torre de los Escipiones",
            "Arco de Bará",
            "Villa Romana de los Munts",
            "Mausoleo de Centcelles",
        ],
        "stop_instructions": "Diríjase en vehículo hacia {title}.",
        "stop_minutes": 40,
    },
]
