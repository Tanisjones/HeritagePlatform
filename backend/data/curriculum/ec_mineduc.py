"""Curriculum-standard catalog — Ecuador, MinEduc (Currículo Nacional).

Heritage-education-relevant "destrezas con criterios de desempeño", adapted and
paraphrased per subject and subnivel for the plan editor's alignment picker.
Loaded by ``manage.py seed_curriculum`` (idempotent update_or_create per code).

Code convention (matches the original migration-seeded entries):
  <AREA>.<subnivel>.<bloque>.<n> — subnivel digit: 1 Preparatoria ·
  2 Básica elemental · 3 Básica media · 4 Básica superior · 5 Bachillerato.
"""

COUNTRY = "EC"
FRAMEWORK = "MinEduc"

GRADE_BY_LEVEL = {
    "1": "Preparatoria",
    "2": "Básica elemental",
    "3": "Básica media",
    "4": "Básica superior",
    "5": "Bachillerato",
}


def grade_for(code):
    """Derive the grade level from the code's subnivel digit (2nd segment)."""
    try:
        return GRADE_BY_LEVEL[code.split(".")[1][0]]
    except (IndexError, KeyError):
        return ""


# (code, subject, description) — grade_level derives from the code.
STANDARDS = [
    # ── Estudios Sociales (CS) ─────────────────────────────────────────────
    ("CS.1.1.1", "Estudios Sociales",
     "Reconocer los espacios significativos de la familia y la escuela como parte de su historia personal."),
    ("CS.1.2.2", "Estudios Sociales",
     "Identificar los lugares emblemáticos de su barrio o comunidad y las actividades que allí se realizan."),
    ("CS.2.1.3", "Estudios Sociales",
     "Describir la historia de su localidad a partir de relatos familiares, fotografías y objetos antiguos."),
    ("CS.2.1.4", "Estudios Sociales",
     "Reconocer los edificios, plazas y monumentos representativos de la ciudad y su función social."),
    ("CS.2.2.5", "Estudios Sociales",
     "Distinguir fiestas, tradiciones y costumbres de la comunidad y valorar su significado."),
    ("CS.2.3.6", "Estudios Sociales",
     "Ubicar en el espacio local los sitios naturales y culturales importantes usando croquis y planos sencillos."),
    ("CS.3.1.10", "Estudios Sociales",
     "Reconocer y valorar el patrimonio cultural del entorno local como parte de la identidad."),
    ("CS.3.1.11", "Estudios Sociales",
     "Analizar los cambios y permanencias del espacio urbano a partir de fuentes históricas locales."),
    ("CS.3.2.12", "Estudios Sociales",
     "Explicar el papel de los mercados, ferias y oficios tradicionales en la economía local."),
    ("CS.3.2.13", "Estudios Sociales",
     "Investigar el origen y significado de los nombres de calles, plazas y parroquias de la ciudad."),
    ("CS.3.3.14", "Estudios Sociales",
     "Valorar la diversidad cultural de los pueblos y nacionalidades presentes en la localidad."),
    ("CS.4.1.1", "Estudios Sociales",
     "Analizar la historia de la localidad a partir de su patrimonio material e inmaterial."),
    ("CS.4.1.2", "Estudios Sociales",
     "Contrastar fuentes primarias y secundarias sobre acontecimientos históricos de la región."),
    ("CS.4.2.3", "Estudios Sociales",
     "Examinar los procesos de independencia y su huella en los espacios y monumentos de la ciudad."),
    ("CS.4.3.4", "Estudios Sociales",
     "Debatir sobre la conservación del patrimonio frente al crecimiento urbano y el turismo."),
    ("CS.5.1.5", "Estudios Sociales",
     "Investigar procesos históricos nacionales a partir de estudios de caso del patrimonio local."),
    ("CS.5.2.6", "Estudios Sociales",
     "Evaluar políticas públicas de gestión y salvaguarda del patrimonio cultural en el Ecuador."),

    # ── Educación Cultural y Artística (ECA) ───────────────────────────────
    ("ECA.1.1.1", "Educación Cultural y Artística",
     "Explorar sonidos, imágenes y movimientos presentes en las fiestas de su comunidad."),
    ("ECA.1.2.2", "Educación Cultural y Artística",
     "Expresar mediante el juego y el dibujo experiencias vividas en lugares significativos de su entorno."),
    ("ECA.2.1.3", "Educación Cultural y Artística",
     "Observar y describir manifestaciones artísticas presentes en el espacio público de la ciudad."),
    ("ECA.2.3.4", "Educación Cultural y Artística",
     "Explorar manifestaciones culturales y artísticas del patrimonio riobambeño."),
    ("ECA.2.3.5", "Educación Cultural y Artística",
     "Participar en celebraciones y rituales de la comunidad reconociendo sus elementos artísticos."),
    ("ECA.3.1.6", "Educación Cultural y Artística",
     "Indagar sobre los oficios artesanales de la localidad y las técnicas que emplean."),
    ("ECA.3.2.6", "Educación Cultural y Artística",
     "Documentar y comunicar expresiones culturales locales mediante distintos lenguajes."),
    ("ECA.3.2.7", "Educación Cultural y Artística",
     "Crear producciones artísticas inspiradas en leyendas, música y danzas tradicionales."),
    ("ECA.3.3.8", "Educación Cultural y Artística",
     "Analizar el valor estético y simbólico de la arquitectura patrimonial de la ciudad."),
    ("ECA.4.1.9", "Educación Cultural y Artística",
     "Investigar la obra de artistas y artesanos locales y su relación con la identidad cultural."),
    ("ECA.4.2.10", "Educación Cultural y Artística",
     "Producir registros audiovisuales de manifestaciones del patrimonio inmaterial local."),
    ("ECA.4.3.11", "Educación Cultural y Artística",
     "Debatir el papel del arte urbano y contemporáneo en la resignificación del patrimonio."),
    ("ECA.5.1.12", "Educación Cultural y Artística",
     "Diseñar proyectos culturales que difundan el patrimonio local en la comunidad."),
    ("ECA.5.2.13", "Educación Cultural y Artística",
     "Analizar críticamente los usos sociales y turísticos de las manifestaciones culturales."),

    # ── Ciencias Naturales (CN) ────────────────────────────────────────────
    ("CN.1.3.1", "Ciencias Naturales",
     "Explorar los seres vivos y elementos naturales presentes en parques y espacios de su entorno."),
    ("CN.2.4.2", "Ciencias Naturales",
     "Observar y registrar las características del paisaje natural que rodea a la ciudad."),
    ("CN.2.5.3", "Ciencias Naturales",
     "Identificar plantas y animales propios de la región y su relación con la vida cotidiana."),
    ("CN.3.4.4", "Ciencias Naturales",
     "Explicar la influencia del relieve y el clima en los asentamientos y cultivos locales."),
    ("CN.3.5.1", "Ciencias Naturales",
     "Relacionar el paisaje natural con el patrimonio y su conservación."),
    ("CN.3.5.2", "Ciencias Naturales",
     "Indagar los saberes ancestrales sobre plantas medicinales y alimentarias de la zona."),
    ("CN.4.1.3", "Ciencias Naturales",
     "Analizar los ecosistemas cercanos a la ciudad y las amenazas derivadas de la actividad humana."),
    ("CN.4.5.4", "Ciencias Naturales",
     "Evaluar el impacto ambiental sobre los bienes patrimoniales y proponer medidas de mitigación."),
    ("CN.5.5.5", "Ciencias Naturales",
     "Investigar la relación entre biodiversidad, cultura y sostenibilidad en el territorio."),

    # ── Lengua y Literatura (LL) ───────────────────────────────────────────
    ("LL.1.5.1", "Lengua y Literatura",
     "Escuchar y disfrutar relatos, rimas y arrullos de la tradición oral de su comunidad."),
    ("LL.2.1.2", "Lengua y Literatura",
     "Narrar leyendas y cuentos de la tradición local con secuencia lógica."),
    ("LL.2.5.3", "Lengua y Literatura",
     "Reconocer coplas, adivinanzas y canciones tradicionales como parte de la cultura oral."),
    ("LL.3.1.4", "Lengua y Literatura",
     "Recopilar y reescribir relatos de la tradición oral local a partir de entrevistas."),
    ("LL.3.5.5", "Lengua y Literatura",
     "Analizar leyendas locales identificando personajes, escenarios y elementos simbólicos."),
    ("LL.4.1.6", "Lengua y Literatura",
     "Producir textos expositivos sobre el patrimonio local con fuentes documentales."),
    ("LL.4.5.7", "Lengua y Literatura",
     "Comparar versiones de una misma leyenda y explicar sus variaciones culturales."),
    ("LL.5.1.8", "Lengua y Literatura",
     "Redactar ensayos argumentativos sobre la importancia de salvaguardar el patrimonio inmaterial."),
    ("LL.5.5.9", "Lengua y Literatura",
     "Analizar la literatura ecuatoriana que retrata espacios y memorias de las ciudades."),

    # ── Matemática (M) ─────────────────────────────────────────────────────
    ("M.2.2.1", "Matemática",
     "Medir y comparar longitudes y distancias en recorridos por el entorno cercano."),
    ("M.2.3.2", "Matemática",
     "Reconocer figuras geométricas en fachadas, plazas y objetos del entorno."),
    ("M.3.2.3", "Matemática",
     "Calcular perímetros y áreas a partir de mediciones de espacios patrimoniales."),
    ("M.3.3.4", "Matemática",
     "Interpretar planos y escalas para ubicar sitios de interés en la ciudad."),
    ("M.3.4.5", "Matemática",
     "Recolectar y representar datos estadísticos sobre visitas y usos de espacios públicos."),
    ("M.4.2.6", "Matemática",
     "Aplicar proporcionalidad y semejanza al análisis de elementos arquitectónicos."),
    ("M.4.4.7", "Matemática",
     "Analizar datos de encuestas sobre percepción del patrimonio usando medidas estadísticas."),
    ("M.5.3.8", "Matemática",
     "Modelar matemáticamente rutas óptimas entre sitios de interés patrimonial."),

    # ── Educación Física (EF) ──────────────────────────────────────────────
    ("EF.2.3.1", "Educación Física",
     "Practicar juegos tradicionales de la comunidad reconociendo sus reglas y origen."),
    ("EF.3.3.2", "Educación Física",
     "Ejecutar danzas folclóricas locales identificando sus pasos y significados."),
    ("EF.4.3.3", "Educación Física",
     "Organizar caminatas y recorridos seguros por espacios naturales y patrimoniales."),
]
