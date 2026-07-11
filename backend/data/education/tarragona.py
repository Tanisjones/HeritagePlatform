"""Shared educational content for Tarragona (EducationalResource + LessonPlan).

Consumed by ``manage.py seed_education tarragona``. Content reuses the seeded
Tarragona heritage items (see data/cities/tarragona.py). Spain has no seeded
CurriculumStandard rows yet, so lesson plans align via free-text
``curriculum_alignment`` (LOMLOE competencies) rather than ``standard_codes``.
Rich text uses only the tags allowed by apps/education/sanitize.py.
"""

CITY_SLUG = "tarragona"

RESOURCES = [
    {
        "title": "Tárraco: capital romana y Patrimonio de la Humanidad",
        "type": "articulo",
        "category": "historia",
        "description": (
            "Introducción a la Tarragona romana —Tárraco— y a los monumentos que le "
            "valieron la declaración de la UNESCO en el año 2000."
        ),
        "content": (
            "<h2>La capital de la Hispania Citerior</h2>"
            "<p><strong>Tárraco</strong> fue una de las ciudades más importantes de la "
            "Hispania romana y capital de la provincia <em>Hispania Citerior "
            "Tarraconensis</em>. Su conjunto arqueológico es "
            "<strong>Patrimonio de la Humanidad</strong> por la UNESCO desde el año 2000.</p>"
            "<h2>Un paseo por la ciudad antigua</h2>"
            "<ul>"
            "<li>Las <strong>murallas</strong>, el tramo romano más antiguo fuera de Italia.</li>"
            "<li>El <strong>anfiteatro</strong> junto al mar, para combates de gladiadores.</li>"
            "<li>El <strong>circo</strong>, para carreras de carros, con 30.000 espectadores.</li>"
            "<li>El <strong>acueducto de les Ferreres</strong>, el «Pont del Diable».</li>"
            "</ul>"
            "<blockquote>Caminar por Tarragona es caminar sobre veinte siglos de historia.</blockquote>"
        ),
        "related_items": [
            "Murallas Romanas de Tarragona",
            "Anfiteatro Romano de Tarragona",
            "Circo Romano de Tarragona",
            "Acueducto de les Ferreres (Pont del Diable)",
        ],
    },
    {
        "title": "Los castells: torres humanas, Patrimonio Inmaterial",
        "type": "articulo",
        "category": "tradiciones",
        "description": (
            "Qué son los castells, cómo se construyen y por qué la UNESCO los reconoció "
            "como Patrimonio Cultural Inmaterial de la Humanidad."
        ),
        "content": (
            "<h2>Fuerza, equilibrio, valor y seny</h2>"
            "<p>Los <strong>castells</strong> son torres humanas construidas por "
            "<em>colles castelleres</em>. En 2010 la UNESCO los declaró "
            "<strong>Patrimonio Cultural Inmaterial de la Humanidad</strong>.</p>"
            "<h2>Anatomía de una torre</h2>"
            "<p>Cada castell tiene una <em>pinya</em> (la base que sostiene y protege), un "
            "<em>tronc</em> (el cuerpo de la torre) y culmina cuando el "
            "<strong>enxaneta</strong> —normalmente un niño o niña— corona la torre y "
            "levanta la mano al ritmo de la <em>gralla</em>.</p>"
            "<h2>Un valor colectivo</h2>"
            "<p>El lema casteller resume una ética: <strong>fuerza, equilibrio, valor y "
            "seny</strong> (sentido común). Nadie hace un castell solo.</p>"
        ),
        "related_items": [
            "Castells (Torres Humanas)",
            "Fiestas de Santa Tecla",
        ],
    },
    {
        "title": "La cocina del Camp de Tarragona: calçots y romesco",
        "type": "guia-didactica",
        "category": "gastronomia",
        "description": (
            "Una guía sobre la calçotada y la salsa romesco como patrimonio "
            "gastronómico y ritual social del Camp de Tarragona."
        ),
        "content": (
            "<h2>Un ritual de invierno</h2>"
            "<p>La <strong>calçotada</strong> es una comida tradicional de invierno del "
            "Camp de Tarragona. Los <em>calçots</em> (cebollas tiernas) se asan a la "
            "brasa y se comen con las manos, mojados en <strong>salsa romesco</strong>.</p>"
            "<h2>El romesco, receta de familia</h2>"
            "<p>El romesco se elabora con ñoras, tomate, ajo, almendras y avellanas "
            "tostadas, aceite y pan. Cada familia guarda su versión, transmitida de "
            "generación en generación.</p>"
            "<h2>Actividad sugerida</h2>"
            "<p>Pide a los estudiantes que entrevisten a un familiar sobre una receta "
            "tradicional y la compartan en clase, comparando ingredientes y ocasiones.</p>"
        ),
        "related_items": [
            "Calçotada",
            "Salsa Romesco",
            "Barrio del Serrallo",
        ],
    },
]

LESSON_PLANS = [
    {
        "title": "Un día en Tárraco: la vida en una ciudad romana",
        "summary": (
            "El alumnado descubre cómo era la vida en la Tárraco romana a partir de sus "
            "monumentos (murallas, anfiteatro, circo, acueducto) y elabora una guía de "
            "viaje de la ciudad antigua."
        ),
        "objectives": [
            "Situar Tárraco en el contexto del Imperio romano en Hispania.",
            "Relacionar cada monumento con una función de la vida urbana romana.",
            "Elaborar una breve guía de viaje de la Tárraco romana.",
        ],
        "subject": "Geografía e Historia",
        "grade_level": "Educación Secundaria (1º-2º ESO)",
        "audience": "teacher",
        "pedagogical_approach": "inquiry",
        "estimated_total_minutes": 120,
        "status": "published",
        "visibility": "public",
        "curriculum_alignment": (
            "Geografía e Historia (LOMLOE) — El mundo clásico: Roma y su legado en "
            "Hispania; patrimonio y su conservación."
        ),
        "route_title": "Ruta de la Tárraco Romana",
        "activities": [
            {
                "title": "¿Qué haría un romano en un día?",
                "activity_type": "hook",
                "duration_minutes": 15,
                "instructions": (
                    "<p>Proyecta una imagen del <strong>anfiteatro</strong> junto al mar y "
                    "pregunta: ¿para qué servía este lugar? ¿qué otras cosas necesitaba una "
                    "ciudad romana para funcionar? Recoge hipótesis.</p>"
                ),
                "materials": "Imagen del anfiteatro.",
                "heritage_item_title": "Anfiteatro Romano de Tarragona",
            },
            {
                "title": "Tárraco, capital romana",
                "activity_type": "explain",
                "duration_minutes": 25,
                "instructions": (
                    "<p>Lee el recurso <em>«Tárraco: capital romana»</em> y sitúa la ciudad "
                    "en el mapa del Imperio. Explica qué es un conjunto Patrimonio de la "
                    "Humanidad.</p>"
                ),
                "materials": "Recurso 'Tárraco: capital romana'; mapa del Imperio romano.",
                "heritage_item_title": "Murallas Romanas de Tarragona",
            },
            {
                "title": "Cada monumento, una función",
                "activity_type": "explore",
                "duration_minutes": 45,
                "instructions": (
                    "<p>Con el recorrido <strong>«Ruta de la Tárraco Romana»</strong>, los "
                    "estudiantes asocian cada monumento con una función: ocio "
                    "(anfiteatro, circo), defensa (murallas), abastecimiento (acueducto). "
                    "Completan una tabla.</p>"
                ),
                "materials": "Acceso al recorrido; tabla monumento–función.",
                "bind_route": True,
            },
            {
                "title": "Guía de viaje a la Tárraco romana",
                "activity_type": "practice",
                "duration_minutes": 25,
                "instructions": (
                    "<p>En parejas, elaboran una miniguía (una página) que recomiende tres "
                    "lugares de Tárraco a un viajero, explicando qué ver en cada uno.</p>"
                ),
                "materials": "Plantilla de guía de viaje.",
            },
            {
                "title": "Puesta en común",
                "activity_type": "reflect",
                "duration_minutes": 10,
                "instructions": (
                    "<p>Varias parejas presentan su guía. Cierra: ¿por qué merece la pena "
                    "conservar estos restos dos mil años después?</p>"
                ),
                "materials": "",
            },
        ],
    },
    {
        "title": "Fuerza, equilibrio y seny: los castells como patrimonio vivo",
        "summary": (
            "El alumnado analiza los castells como Patrimonio Inmaterial de la Humanidad, "
            "comprende su estructura y los valores de cooperación que representan, y "
            "reflexiona sobre el trabajo en equipo."
        ),
        "objectives": [
            "Explicar qué son los castells y por qué son Patrimonio Inmaterial.",
            "Identificar las partes de un castell y el papel de cada persona.",
            "Relacionar el lema casteller con valores de cooperación y responsabilidad.",
        ],
        "subject": "Educación en Valores / Cultura y Patrimonio",
        "grade_level": "Educación Primaria (3er ciclo)",
        "audience": "teacher",
        "pedagogical_approach": "collaborative",
        "estimated_total_minutes": 90,
        "status": "published",
        "visibility": "public",
        "curriculum_alignment": (
            "Educación en Valores Cívicos y Éticos (LOMLOE) — convivencia, cooperación "
            "y patrimonio cultural inmaterial de Cataluña."
        ),
        "activities": [
            {
                "title": "Una torre de personas",
                "activity_type": "hook",
                "duration_minutes": 10,
                "instructions": (
                    "<p>Muestra una imagen de un <strong>castell</strong> y pregunta: "
                    "¿cómo crees que se sostiene? ¿qué pasaría si una persona fallara?</p>"
                ),
                "materials": "Imagen de un castell.",
                "heritage_item_title": "Castells (Torres Humanas)",
            },
            {
                "title": "Anatomía de un castell",
                "activity_type": "explain",
                "duration_minutes": 25,
                "instructions": (
                    "<p>Lee el recurso <em>«Los castells»</em> e identifica con la clase la "
                    "<em>pinya</em>, el <em>tronc</em> y el <strong>enxaneta</strong>. "
                    "Comenta el lema: fuerza, equilibrio, valor y seny.</p>"
                ),
                "materials": "Recurso 'Los castells: torres humanas'.",
                "heritage_item_title": "Castells (Torres Humanas)",
            },
            {
                "title": "Construimos una pinya (simbólica)",
                "activity_type": "practice",
                "duration_minutes": 35,
                "instructions": (
                    "<p>En grupos, realizan un juego cooperativo (por ejemplo, sostener "
                    "entre todos un objeto sin que caiga) y luego dialogan: ¿qué papel tuvo "
                    "cada uno? ¿por qué la base es tan importante como la cima?</p>"
                ),
                "materials": "Espacio amplio; objeto ligero para el juego.",
            },
            {
                "title": "Lo que aprendemos de una torre humana",
                "activity_type": "reflect",
                "duration_minutes": 20,
                "instructions": (
                    "<p>Cada grupo escribe una frase que conecte los castells con la vida "
                    "en el aula: ¿dónde necesitamos fuerza, equilibrio, valor y seny en "
                    "nuestro día a día?</p>"
                ),
                "materials": "Cartulinas.",
            },
        ],
    },
]
