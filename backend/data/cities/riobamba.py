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
            "description": "Catedral histórica distinguida por su fachada barroca, rescatada piedra a piedra de las ruinas de la antigua Riobamba tras el terremoto de 1797 y reconstruida en su emplazamiento actual entre 1810 y 1835. Su portada combina elementos decorativos indígenas y españoles, y preside el Parque Maldonado.",
            "location": Point(-78.6478, -1.6722),
            "address": "5 de Junio, entre José Veloz y Espejo",
            "parish": "Veloz",
            "heritage_type": "tangible",
            "heritage_category": "architecture",
            "historical_period": "colonial",
            "status": "published",
            "media": [
                {"type": "image", "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Catedral%20de%20Riobamba%2C%20Interior.jpg"},
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
            "description": "La plaza principal de Riobamba y primera plaza planificada de la ciudad (antigua Plaza Mayor), nombrada en honor al sabio riobambeño Pedro Vicente Maldonado. Rodeada por la Catedral y edificios patrimoniales, sirve como punto de encuentro central y escenario de actividades cívicas.",
            "location": Point(-78.6483, -1.6727),
            "address": "Primera Constituyente y Espejo",
            "parish": "Maldonado",
            "heritage_type": "tangible",
            "heritage_category": "architecture",
            "historical_period": "republican",
            "status": "published",
            "media": [
                {"type": "image", "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Ecuador%20Riobamba%20ParqueMaldonada.JPG"}
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
            "description": "Plato tradicional de cerdo asado entero, emblema de la gastronomía riobambeña, servido con llapingachos, mote, tortillas de papa y ají de chiriucho. Su epicentro es el Mercado La Merced, donde las 'hornaderas' lo sirven en puestos con décadas de tradición.",
            "location": Point(-78.6502, -1.6738),
            "address": "Mercado La Merced, Guayaquil y Colón",
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
            "title": "Pase del Niño",
            "description": "Colorida festividad religiosa celebrada entre diciembre y febrero, con procesiones que recorren el centro histórico acompañadas de personajes tradicionales como el Curiquingue, el Diablo Huma y bandas de pueblo. Declarada Patrimonio Cultural Inmaterial del cantón Riobamba; se celebra desde inicios del siglo XX.",
            "location": Point(-78.6486, -1.6725),
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
            "description": "Teatro histórico de arquitectura neoclásica frente al Parque Sucre. Construido desde 1918 como residencia de la familia León Romero, abrió como teatro en 1929. Restaurado y reinaugurado en 2021, hoy es sede de la Orquesta Sinfónica Municipal de Riobamba.",
            "location": Point(-78.6507, -1.6713),
            "address": "Primera Constituyente y España",
            "parish": "Maldonado",
            "heritage_type": "tangible",
            "heritage_category": "architecture",
            "historical_period": "republican",
            "status": "published",
            "media": [{"type": "image", "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Teatro%20Le%C3%B3n%20%28Riobamba%2C%20Ecuador%201920%29.png"}],
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
            "description": "Reconocida como la primera iglesia católica de Ecuador, inaugurada el 15 de agosto de 1534 junto a la laguna de Colta. Tras el terremoto de 1977 el templo fue reconstruido en gran parte; solo la fachada de piedra, con detalles de talla indígena, conserva elementos originales del siglo XVI.",
            "location": Point(-78.7626, -1.7235),
            "address": "Colta, Panamericana Sur",
            "parish": "Cacha", # Approximation
            "heritage_type": "tangible",
            "heritage_category": "architecture",
            "historical_period": "colonial",
            "status": "published",
            "media": [{"type": "image", "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Iglesia%20de%20Balbanera%2001.jpg"}],
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
            "description": "Estación de tren de Riobamba, inaugurada el 1 de enero de 1925 y parada clave del ferrocarril transandino que unió la costa con la sierra. Símbolo de la modernización del país a inicios del siglo XX, el complejo alberga hoy un museo del tren.",
            "location": Point(-78.6538, -1.6698),
            "address": "Av. Daniel León Borja y Carabobo",
            "parish": "Lizarzaburu",
            "heritage_type": "tangible",
            "heritage_category": "architecture",
            "historical_period": "republican",
            "status": "published",
            "media": [{"type": "image", "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Estaci%C3%B3n%20de%20Tren%20de%20Riobamba%20Ecuador%201475.jpg"}],
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
            "description": "Museo de Arte Religioso ubicado en el Convento de la Inmaculada Concepción (Madres Conceptas). Inaugurado en 1980, exhibe pintura y escultura de la Escuela Quiteña, ornamentos coloniales y su pieza más célebre: la Custodia de Riobamba, una joya de oro y piedras preciosas.",
            "location": Point(-78.6490, -1.6710),
            "address": "Argentinos y Juan Larrea",
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
            "description": "Mercado tradicional junto a la iglesia de San Francisco, conocido por sus puestos de comida típica —hornado, yaguarlocro, jugos— y por sus flores y artesanías. Es un bullicioso centro social y económico del casco histórico.",
            "location": Point(-78.6471, -1.6748),
            "address": "Primera Constituyente, junto a la iglesia de San Francisco",
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
            "description": "Danza ancestral andina en honor al curiquingue, ave considerada sagrada por los incas y augurio de buenas cosechas. Los danzantes visten grandes alas de colores y un tocado con pico, imitando los movimientos del ave; suele formar parte de las procesiones del Pase del Niño.",
            "location": Point(-78.6470, -1.6735),
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
            "description": "Versos ingeniosos y rimados que se cantan durante el Carnaval en Chimborazo y toda la sierra ecuatoriana, expresando alegría, coqueteo, sátira social y lazos comunitarios. Tradición oral viva que se transmite de generación en generación.",
            "location": Point(-78.6500, -1.6712),
            "address": "Provincia de Chimborazo",
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
            "description": "Leyenda colonial que explica la cabeza cortada del escudo de Riobamba. Hacia 1575, un médico extranjero apodado «el Luterano» habría agredido a un sacerdote durante la fiesta de San Pedro; su castigo quedó grabado en el imaginario y en la heráldica de la ciudad. Se asocia tradicionalmente al antiguo barrio artesanal de Santa Rosa.",
            "location": Point(-78.6492, -1.6730),
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
            "description": "Bebida tradicional de la zona de Riobamba y Guano, elaborada con chicha de jora, panela, huevo crudo, cerveza y un chorro de licor. Se sirve batida y espumosa, es popular en Carnaval y se le atribuyen propiedades energéticas.",
            "location": Point(-78.6455, -1.6740),
            "address": "Riobamba y Guano (Chimborazo)",
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
            "description": "Fritada de cerdo cocida lentamente en su propia grasa, plato clásico de la sierra ecuatoriana. En los mercados de Riobamba se sirve con mote, papas, tostado y maíz, y forma parte del recorrido gastronómico de la ciudad.",
            "location": Point(-78.6478, -1.6742),
            "address": "Mercados de Riobamba",
            "parish": "Lizarzaburu",
            "heritage_type": "intangible",
            "heritage_category": "gastronomy",
            "historical_period": "contemporary",
            "status": "published",
            "media": [],
             "moderation": {
                "score": {"completeness": 37, "accuracy": 30, "media": 24, "notes": "Deliciosa."},
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
