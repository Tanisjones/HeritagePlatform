"""
Riobamba, Ecuador — the founding city's demo dataset.

Consumed by scripts/seed_city_engine.py (via `manage.py seed_city riobamba`
or the legacy `manage.py seed_heritage`). To onboard another city, copy this
module's structure into data/cities/<slug>.py and run `seed_city <slug>`.

NOTE: the PARISHES/ITEMS literals were lifted byte-exact from the legacy
scripts/seed_heritage.py, so continuation lines keep their original
indentation (harmless inside brackets).
"""

from datetime import timedelta

from django.contrib.gis.geos import Point


CITY = {
    "slug": "riobamba",
    "name": "Riobamba",
    "name_es": "Riobamba",
    "country": "EC",
    "country_name": "Ecuador",
    "country_name_es": "Ecuador",
    "region": "Chimborazo",
    "timezone": "America/Guayaquil",
    "center": (-78.6479, -1.6735),  # lng, lat
    "default_zoom": 13,
    "default_language": "es",
}

PARISHES = [
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

ITEMS = [
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

ROUTES = [
    {
        "title": "Paseo del Centro Histórico",
        "description": (
            "Un recorrido por el corazón arquitectónico e histórico de Riobamba, "
            "visitando hitos republicanos y coloniales."
        ),
        "theme": "Historia y Arquitectura",
        "difficulty": "easy",
        "estimated_duration": timedelta(hours=2),
        "distance": 1.5,
        "best_season": "year_round",
        "accessibility_notes": "La mayoría de las calles están pavimentadas pero algunas aceras son estrechas.",
        "wheelchair_accessible": True,
        "item_titles": [
            "Parque Maldonado",
            "Catedral de Riobamba",
            "Teatro León",
            "Museo de las Conceptas",
            "Estación del Ferrocarril",
        ],
        "stop_instructions": "Camine hacia {title}.",
        "stop_minutes": 20,
    },
    {
        "title": "Ruta Gastronómica de Riobamba",
        "description": (
            "Saboree los sabores auténticos de la ciudad, desde el famoso Hornado "
            "hasta la tradicional Chicha."
        ),
        "theme": "Gastronomía",
        "difficulty": "medium",
        "estimated_duration": timedelta(hours=3),
        "distance": 2.0,
        "best_season": "year_round",
        "estimated_cost": 15.00,
        "cost_notes": "Estimado por persona para degustación.",
        "item_titles": [
            "Hornado de Riobamba",
            "Fritada de Cajón",
            "Chicha Huevona",
            "Mercado San Francisco",
        ],
        "stop_instructions": "Siguiente parada para degustar.",
        "stop_minutes": 40,
    },
]
