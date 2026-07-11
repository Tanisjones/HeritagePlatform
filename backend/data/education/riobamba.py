"""Shared educational content for Riobamba (EducationalResource + LessonPlan).

Consumed by ``manage.py seed_education riobamba``. Content reuses the seeded
Riobamba heritage items (see data/cities/riobamba.py) and aligns lesson plans to
real Ecuadorian MinEduc curriculum standards (see data/curriculum/ec_mineduc.py,
loaded via ``seed_curriculum``). Rich text uses only the tags allowed by
apps/education/sanitize.py (headings, p, ul/ol, strong/em, blockquote, table…).

Keys:
  RESOURCES     — standalone articles/guides tied to heritage items.
  LESSON_PLANS  — structured, multi-activity teacher plans with standards.
"""

CITY_SLUG = "riobamba"

RESOURCES = [
    {
        "title": "Riobamba colonial: la ciudad que renació tras el terremoto de 1797",
        "type": "articulo",
        "category": "historia",
        "description": (
            "Un recorrido por la reconstrucción de Riobamba tras el gran terremoto "
            "de 1797 y por los monumentos que conservan la memoria de la antigua ciudad."
        ),
        "content": (
            "<h2>Una ciudad trasladada</h2>"
            "<p>El 4 de febrero de 1797 un violento terremoto destruyó la antigua "
            "Riobamba. La ciudad fue <strong>refundada en la llanura de Tapi</strong>, "
            "su emplazamiento actual, y con ella se levantó un nuevo trazado urbano en "
            "damero alrededor del <em>Parque Maldonado</em>.</p>"
            "<h2>Piedras con memoria</h2>"
            "<p>La <strong>Catedral de Riobamba</strong> es el testimonio más elocuente "
            "de aquella catástrofe: su portada barroca fue rescatada piedra a piedra de "
            "las ruinas de la ciudad antigua y reconstruida entre 1810 y 1835. En su "
            "decoración conviven motivos indígenas y españoles, un rasgo del "
            "<em>mestizaje</em> artístico de la Sierra.</p>"
            "<blockquote>La fachada de la Catedral es, literalmente, la vieja Riobamba "
            "reensamblada en la nueva.</blockquote>"
            "<h2>Para seguir explorando</h2>"
            "<ul>"
            "<li>El <strong>Parque Maldonado</strong>, primera plaza planificada de la ciudad.</li>"
            "<li>El <strong>Teatro León</strong>, joya del neoclásico republicano.</li>"
            "<li>El <strong>Museo de las Conceptas</strong> y su Custodia de Riobamba.</li>"
            "</ul>"
        ),
        "related_items": [
            "Catedral de Riobamba",
            "Parque Maldonado",
            "Teatro León",
            "Museo de las Conceptas",
        ],
    },
    {
        "title": "Sabores de Riobamba: el hornado y la mesa festiva",
        "type": "articulo",
        "category": "gastronomia",
        "description": (
            "El hornado como plato-emblema de la identidad riobambeña: de dónde viene, "
            "cómo se sirve y por qué el Mercado La Merced es su templo."
        ),
        "content": (
            "<h2>El rey de la mesa</h2>"
            "<p>El <strong>hornado</strong> —cerdo asado entero— es el plato más "
            "representativo de la cocina riobambeña. Se sirve con "
            "<em>llapingachos</em>, mote, tortillas de papa y un ají de "
            "<em>chiriucho</em> que lo acompaña.</p>"
            "<h2>El Mercado La Merced</h2>"
            "<p>Su epicentro es el <strong>Mercado La Merced</strong>, donde las "
            "<em>hornaderas</em> —cocineras con décadas de oficio— atienden puestos "
            "que se heredan de madres a hijas. Comer hornado allí es también "
            "participar de un ritual social.</p>"
            "<h2>Más allá del hornado</h2>"
            "<p>La tradición festiva de Chimborazo ofrece otras delicias como la "
            "<strong>fritada</strong> y la <strong>chicha huevona</strong>, bebida de "
            "la zona de Riobamba y Guano popular en Carnaval.</p>"
        ),
        "related_items": [
            "Hornado de Riobamba",
            "Mercado San Francisco",
            "Fritada de Cajón",
            "Chicha Huevona",
        ],
    },
    {
        "title": "Leyendas y tradición oral de Chimborazo",
        "type": "articulo",
        "category": "tradiciones",
        "description": (
            "Cómo la tradición oral —leyendas, coplas y danzas— guarda la memoria y "
            "los valores de la comunidad riobambeña."
        ),
        "content": (
            "<h2>La memoria que se cuenta</h2>"
            "<p>Antes que los libros, fue la voz. En Chimborazo, las "
            "<strong>leyendas</strong> explican el mundo y transmiten valores. La "
            "<em>Leyenda del Luterano</em>, por ejemplo, explica la cabeza cortada del "
            "escudo de Riobamba a partir de un suceso ocurrido hacia 1575.</p>"
            "<h2>Coplas y danzas</h2>"
            "<p>En Carnaval, las <strong>coplas</strong> —versos rimados, a menudo "
            "picarescos— tejen el humor y la crítica social de los pueblos. Y en las "
            "procesiones del <em>Pase del Niño</em> danza el "
            "<strong>Curiquingue</strong>, ave sagrada de los Andes, con sus grandes "
            "alas de colores.</p>"
            "<h2>Un patrimonio vivo</h2>"
            "<p>Estas expresiones no están en vitrinas: se cantan, se bailan y se "
            "cuentan cada año. Documentarlas y practicarlas es mantenerlas vivas.</p>"
        ),
        "related_items": [
            "Leyenda del Luterano",
            "Coplas del Carnaval",
            "Danza de los Curiquingues",
            "Pase del Niño",
        ],
    },
    {
        "title": "Guía de lectura del patrimonio arquitectónico riobambeño",
        "type": "guia-didactica",
        "category": "arte-arquitectura",
        "description": (
            "Una guía breve para que estudiantes aprendan a 'leer' un edificio "
            "histórico: estilo, materiales, función y contexto."
        ),
        "content": (
            "<h2>¿Cómo se lee un edificio?</h2>"
            "<p>Observar patrimonio es más que mirar. Propón a tus estudiantes cuatro "
            "preguntas ante cada monumento:</p>"
            "<ol>"
            "<li><strong>¿Qué estilo tiene?</strong> Barroco, neoclásico, republicano…</li>"
            "<li><strong>¿De qué está hecho?</strong> Piedra, adobe, ladrillo, hierro.</li>"
            "<li><strong>¿Para qué se construyó?</strong> Culto, poder, comercio, transporte.</li>"
            "<li><strong>¿Qué nos dice de su época?</strong></li>"
            "</ol>"
            "<h2>Tres casos para practicar</h2>"
            "<table>"
            "<thead><tr><th>Edificio</th><th>Estilo</th><th>Función original</th></tr></thead>"
            "<tbody>"
            "<tr><td>Catedral de Riobamba</td><td>Barroco</td><td>Culto religioso</td></tr>"
            "<tr><td>Teatro León</td><td>Neoclásico</td><td>Residencia, luego teatro</td></tr>"
            "<tr><td>Estación del Ferrocarril</td><td>Republicano</td><td>Transporte</td></tr>"
            "</tbody>"
            "</table>"
            "<p><em>Sugerencia:</em> combina esta guía con una visita al centro "
            "histórico o con el recorrido «Paseo del Centro Histórico».</p>"
        ),
        "related_items": [
            "Catedral de Riobamba",
            "Teatro León",
            "Estación del Ferrocarril",
        ],
    },
]

LESSON_PLANS = [
    {
        "title": "Nuestro centro histórico: leer la ciudad de Riobamba",
        "summary": (
            "Los estudiantes reconocen los edificios y plazas emblemáticos del centro "
            "histórico de Riobamba, comprenden su origen tras el terremoto de 1797 y "
            "elaboran una ficha patrimonial de un monumento."
        ),
        "objectives": [
            "Identificar los monumentos representativos del centro histórico de Riobamba.",
            "Relacionar la reconstrucción de la ciudad con el terremoto de 1797.",
            "Elaborar una ficha patrimonial sencilla de un edificio.",
        ],
        "subject": "Estudios Sociales",
        "grade_level": "Básica elemental",
        "audience": "teacher",
        "pedagogical_approach": "inquiry",
        "estimated_total_minutes": 120,
        "status": "published",
        "visibility": "public",
        "curriculum_alignment": "Estudios Sociales — Patrimonio local (CS.2.1.4, CS.2.3.6)",
        "standard_codes": ["CS.2.1.4", "CS.2.3.6", "CS.2.1.3"],
        "route_title": "Paseo del Centro Histórico",
        "activities": [
            {
                "title": "¿Qué sabemos de nuestra ciudad?",
                "activity_type": "hook",
                "duration_minutes": 15,
                "instructions": (
                    "<p>Muestra a la clase una foto del <strong>Parque Maldonado</strong> "
                    "y pregunta: ¿reconoces este lugar? ¿qué edificios lo rodean? Anota "
                    "en la pizarra lo que el grupo ya sabe.</p>"
                ),
                "materials": "Proyector o impresión de la imagen del parque.",
                "heritage_item_title": "Parque Maldonado",
            },
            {
                "title": "La ciudad que renació",
                "activity_type": "explain",
                "duration_minutes": 25,
                "instructions": (
                    "<p>Lee con la clase el recurso <em>«Riobamba colonial»</em> y explica "
                    "cómo el terremoto de 1797 obligó a trasladar la ciudad. Destaca que la "
                    "portada de la <strong>Catedral</strong> se rescató de las ruinas antiguas.</p>"
                ),
                "materials": "Recurso 'Riobamba colonial' (biblioteca de la plataforma).",
                "heritage_item_title": "Catedral de Riobamba",
            },
            {
                "title": "Recorrido por el centro histórico",
                "activity_type": "explore",
                "duration_minutes": 45,
                "instructions": (
                    "<p>Realiza (presencial o virtualmente, con el mapa de la plataforma) "
                    "el recorrido <strong>«Paseo del Centro Histórico»</strong>. En cada "
                    "parada, los estudiantes anotan el nombre del edificio y una "
                    "característica que les llame la atención.</p>"
                ),
                "materials": "Cuaderno de campo; acceso al recorrido en la plataforma.",
                "bind_route": True,
            },
            {
                "title": "Mi ficha patrimonial",
                "activity_type": "practice",
                "duration_minutes": 25,
                "instructions": (
                    "<p>Cada estudiante elige un monumento y completa una ficha con: "
                    "nombre, para qué se construyó, de qué está hecho y por qué es "
                    "importante para Riobamba.</p>"
                ),
                "materials": "Plantilla de ficha patrimonial.",
            },
            {
                "title": "Ponemos en común",
                "activity_type": "reflect",
                "duration_minutes": 10,
                "instructions": (
                    "<p>Algunos estudiantes comparten su ficha. Cierra preguntando: "
                    "¿por qué es importante cuidar estos edificios?</p>"
                ),
                "materials": "",
            },
        ],
    },
    {
        "title": "Sabores y leyendas: patrimonio inmaterial de Riobamba",
        "summary": (
            "Los estudiantes exploran el patrimonio inmaterial de Riobamba —su "
            "gastronomía festiva y su tradición oral— y crean una copla o una ficha "
            "de un plato tradicional, valorando la memoria colectiva."
        ),
        "objectives": [
            "Reconocer manifestaciones del patrimonio inmaterial de Chimborazo.",
            "Analizar una leyenda local identificando personajes y valores.",
            "Crear una copla o ficha gastronómica que difunda una tradición local.",
        ],
        "subject": "Educación Cultural y Artística",
        "grade_level": "Básica media",
        "audience": "teacher",
        "pedagogical_approach": "project_based",
        "estimated_total_minutes": 135,
        "status": "published",
        "visibility": "public",
        "curriculum_alignment": (
            "Educación Cultural y Artística y Lengua — Patrimonio inmaterial y "
            "tradición oral (ECA.3.1.6, LL.3.5.5)"
        ),
        "standard_codes": ["ECA.3.1.6", "LL.3.5.5", "LL.3.1.4"],
        "route_title": "Ruta Gastronómica de Riobamba",
        "activities": [
            {
                "title": "El mapa de nuestros sabores y relatos",
                "activity_type": "hook",
                "duration_minutes": 15,
                "instructions": (
                    "<p>Pregunta al grupo qué plato típico y qué leyenda de Riobamba "
                    "conocen. Registra sus respuestas en dos columnas: <em>sabores</em> y "
                    "<em>relatos</em>.</p>"
                ),
                "materials": "Pizarra.",
            },
            {
                "title": "El hornado y la mesa festiva",
                "activity_type": "explore",
                "duration_minutes": 30,
                "instructions": (
                    "<p>Lee el recurso <em>«Sabores de Riobamba»</em>. Comenta el papel del "
                    "<strong>Mercado La Merced</strong> y de las hornaderas como "
                    "guardianas de un saber que se transmite en familia.</p>"
                ),
                "materials": "Recurso 'Sabores de Riobamba'.",
                "heritage_item_title": "Hornado de Riobamba",
            },
            {
                "title": "Leyendas que explican el mundo",
                "activity_type": "explain",
                "duration_minutes": 30,
                "instructions": (
                    "<p>Lee la <strong>Leyenda del Luterano</strong> y analiza con la clase: "
                    "¿quiénes son los personajes? ¿qué explica la leyenda sobre el escudo "
                    "de la ciudad? ¿qué valores transmite?</p>"
                ),
                "materials": "Ficha de la leyenda (plataforma).",
                "heritage_item_title": "Leyenda del Luterano",
            },
            {
                "title": "Creamos patrimonio: copla o ficha de sabor",
                "activity_type": "practice",
                "duration_minutes": 45,
                "instructions": (
                    "<p>En grupos, los estudiantes eligen una opción:</p>"
                    "<ul>"
                    "<li>Escribir una <strong>copla</strong> de Carnaval sobre su ciudad, o</li>"
                    "<li>Elaborar una <strong>ficha</strong> de un plato tradicional "
                    "(ingredientes, ocasión, quién lo prepara).</li>"
                    "</ul>"
                    "<p>Cada grupo comparte su creación con la clase.</p>"
                ),
                "materials": "Hojas, colores; opcional grabadora para las coplas.",
            },
            {
                "title": "¿Por qué vale la pena cuidarlo?",
                "activity_type": "reflect",
                "duration_minutes": 15,
                "instructions": (
                    "<p>Cierra con una conversación: si estas tradiciones no se practican, "
                    "¿qué se pierde? ¿cómo podemos ayudar a mantenerlas vivas?</p>"
                ),
                "materials": "",
            },
        ],
    },
]
