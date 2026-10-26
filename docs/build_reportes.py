"""Genera los reportes de la Entrega 1 (.docx, formato IEEE) a partir de las figuras del EDA,
la maqueta y las capturas de los repositorios.

Uso: python docs/build_reportes.py
"""
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "reports" / "figures"
CAP = ROOT / "reports" / "capturas"
MOCK = ROOT / "mockup"
OUT = ROOT / "docs"

REPO_URL = "https://github.com/mateor0408-sys/proyecto-saber11-dsa"
S3_URL = "s3://mateorios2002-dvcstore/saber11"
FECHA = "25 de octubre de 2026"

FONT = "Times New Roman"
COL_W = Cm(8.4)     # ancho de columna IEEE (≈ 3.3 in)
FULL_W = Cm(17.5)   # ancho de página útil


# ----------------------------------------------------------------------------- utilidades
def set_font(run, size=10, bold=None, italic=None, small_caps=None):
    run.font.name, run.font.size = FONT, Pt(size)
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), FONT)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if small_caps is not None:
        run.font.small_caps = small_caps
    return run


def set_columns(section, n, space_cm=0.64):
    cols = section._sectPr.find(qn("w:cols"))
    if cols is None:
        cols = OxmlElement("w:cols")
        section._sectPr.append(cols)
    cols.set(qn("w:num"), str(n))
    cols.set(qn("w:space"), str(int(Cm(space_cm).twips)))


def new_section(doc, cols):
    sec = doc.add_section(WD_SECTION.CONTINUOUS)
    set_columns(sec, cols)
    return sec


def base_doc():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.5), Inches(11)
    sec.top_margin, sec.bottom_margin = Inches(0.75), Inches(1)
    sec.left_margin = sec.right_margin = Inches(0.625)
    st = doc.styles["Normal"]
    st.font.name, st.font.size = FONT, Pt(10)
    st.element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), FONT)
    pf = st.paragraph_format
    pf.space_before, pf.space_after, pf.line_spacing = Pt(0), Pt(0), 1.0
    return doc


def body(doc, text, lead=None, indent=True):
    """Párrafo justificado con sangría IEEE; `lead` va en itálica (estilo de párrafo con título)."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if indent:
        p.paragraph_format.first_line_indent = Cm(0.36)
    if lead:
        set_font(p.add_run(lead + " "), italic=True)
    set_font(p.add_run(text))
    return p


def section_title(doc, numeral, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(8), Pt(4)
    p.paragraph_format.keep_with_next = True
    set_font(p.add_run(f"{numeral}. {text}" if numeral else text), small_caps=True)
    return p


def subsection(doc, letter, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(4), Pt(2)
    p.paragraph_format.keep_with_next = True
    set_font(p.add_run(f"{letter}. {text}"), italic=True)
    return p


def bullets(doc, items):
    for lead, text in items:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.left_indent = Cm(0.5)
        p.paragraph_format.first_line_indent = Cm(-0.3)
        set_font(p.add_run("• "))
        if lead:
            set_font(p.add_run(lead + " "), italic=True)
        set_font(p.add_run(text))


class Counter:
    def __init__(self):
        self.fig = 0
        self.tab = 0


def figure(doc, cnt, path, caption, width=COL_W):
    cnt.fig += 1
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=width)
    c = doc.add_paragraph()
    c.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY if width == COL_W else WD_ALIGN_PARAGRAPH.CENTER
    c.paragraph_format.space_before, c.paragraph_format.space_after = Pt(3), Pt(8)
    set_font(c.add_run(f"Fig. {cnt.fig}. "), size=8)
    set_font(c.add_run(caption), size=8)
    return cnt.fig


def figure_pair(doc, cnt, left, right):
    """Dos figuras lado a lado a ancho de página; cada argumento es (ruta, pie de figura)."""
    t = doc.add_table(rows=2, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (path, caption) in enumerate((left, right)):
        cnt.fig += 1
        img, cap = t.rows[0].cells[i], t.rows[1].cells[i]
        img.width = cap.width = Cm(8.75)
        img.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        img.paragraphs[0].add_run().add_picture(str(path), width=Cm(8.4))
        cp = cap.paragraphs[0]
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cp.paragraph_format.space_before = Pt(3)
        set_font(cp.add_run(f"Fig. {cnt.fig}. "), size=8)
        set_font(cp.add_run(caption), size=8)
    sp = doc.add_paragraph()
    sp.paragraph_format.space_after = Pt(4)


ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]


def shade(cell, hex_color):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    cell._tc.get_or_add_tcPr().append(shd)


def table(doc, cnt, title, header, rows, widths, size=8):
    cnt.tab += 1
    for text in (f"Tabla {ROMAN[cnt.tab - 1]}", title):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True
        set_font(p.add_run(text), size=8, small_caps=True)
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        set_font(c.paragraphs[0].add_run(h), size=size, bold=True)
        shade(c, "E8E8E8")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            set_font(cells[i].paragraphs[0].add_run(str(v)), size=size)
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
    sp = doc.add_paragraph()
    sp.paragraph_format.space_after = Pt(4)
    return ROMAN[cnt.tab - 1]


def title_block(doc, title, subtitle):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(6)
    set_font(p.add_run(title), size=24)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(p.add_run(subtitle), size=11, italic=True)
    authors = doc.add_table(rows=1, cols=3)
    authors.alignment = WD_TABLE_ALIGNMENT.CENTER
    for cell, name in zip(authors.rows[0].cells, ("Mateo Ríos", "Harol Perafan", "Sebastian Vivas")):
        cell.width = Cm(5.8)
        cp = cell.paragraphs[0]
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cp.paragraph_format.space_before = Pt(8)
        set_font(cp.add_run(name), size=11)
        for line in ("Maestría en Inteligencia Analítica de Datos", "Universidad de los Andes", "Bogotá, Colombia"):
            lp = cell.add_paragraph()
            lp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            set_font(lp.add_run(line), size=9, italic=line.startswith("Maestría"))
    sp = doc.add_paragraph()
    sp.paragraph_format.space_after = Pt(6)


def references(doc, refs):
    section_title(doc, None, "Referencias")
    for i, ref in enumerate(refs, 1):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.left_indent = Cm(0.6)
        p.paragraph_format.first_line_indent = Cm(-0.6)
        p.paragraph_format.space_after = Pt(1)
        set_font(p.add_run(f"[{i}]\t"), size=8)
        set_font(p.add_run(ref), size=8)


# ----------------------------------------------------------------------------- reporte principal
def reporte_entrega():
    doc = base_doc()
    cnt = Counter()
    title_block(doc, "Monitor de Riesgo Académico Saber 11",
                "Proyecto — Entrega 1 · Despliegue de Soluciones Analíticas · " + FECHA)
    new_section(doc, 2)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    set_font(p.add_run("Resumen—"), size=9, bold=True, italic=True)
    set_font(p.add_run(
        "Se propone un producto de datos para identificar, antes de presentar el examen, a los estudiantes y "
        "colegios con mayor riesgo de obtener un puntaje global bajo en Saber 11. A partir de 532.788 registros "
        "públicos del ICFES se construyó un pipeline reproducible versionado con Git y DVC sobre Amazon S3 y se "
        "realizó una exploración orientada a la pregunta de negocio. La educación de la madre, la jornada escolar, "
        "el acceso a computador e internet, el territorio y la naturaleza del colegio concentran el riesgo; por "
        "ejemplo, la tasa de riesgo es 61 % en Chocó frente a 12 % en Bogotá. Con estos hallazgos se iteró la "
        "maqueta de un tablero que combina diagnóstico territorial y predicción individual servida por una API."),
        size=9, bold=True)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(4), Pt(2)
    set_font(p.add_run("Palabras clave—"), size=9, bold=True, italic=True)
    set_font(p.add_run("Saber 11, riesgo académico, aprendizaje supervisado, DVC, tablero, despliegue."),
             size=9, bold=True)

    # I ----------------------------------------------------------------------------------
    section_title(doc, "I", "Introducción: problema y contexto")
    body(doc, "El examen Saber 11 del ICFES evalúa a todos los estudiantes que terminan la educación media en "
              "Colombia. Su puntaje global (0–500) condiciona el acceso a la educación superior, a becas y a "
              "créditos educativos [1]. Los resultados muestran brechas persistentes asociadas al contexto del "
              "estudiante: en el periodo analizado, un estudiante de un colegio en Chocó tiene cinco veces más "
              "probabilidad de quedar en el cuartil inferior que uno de Bogotá (61 % vs. 12 %).")
    body(doc, "Las secretarías de educación y los rectores cuentan con recursos limitados para programas de "
              "refuerzo (preparación pre-Saber, tutorías, conectividad). Hoy la focalización se hace con los "
              "resultados del año anterior, es decir, cuando el estudiante ya presentó la prueba. El problema es la "
              "falta de una herramienta que, con información disponible antes del examen (características del "
              "hogar y del colegio), identifique a tiempo a los estudiantes y colegios con mayor riesgo de bajo "
              "desempeño.")
    body(doc, "Un modelo supervisado entrenado con los resultados históricos permite estimar ese riesgo para cada "
              "estudiante de grado 11 al inicio del año escolar. Combinado con un tablero descriptivo, convierte "
              "los datos abiertos del ICFES en una lista priorizada y explicada de a quién y dónde intervenir.")

    # II ---------------------------------------------------------------------------------
    section_title(doc, "II", "Pregunta de negocio y alcance")
    body(doc, "¿Qué estudiantes (y colegios/municipios) tienen mayor riesgo de obtener un puntaje global bajo en "
              "Saber 11, dadas sus características socioeconómicas y del colegio, para priorizar intervenciones "
              "de refuerzo?", lead="Pregunta de negocio:")
    bullets(doc, [
        ("Usuarios:", "secretarías de educación departamentales y municipales, y rectores de colegios."),
        ("Componente descriptivo:", "tablero con la distribución del riesgo por territorio, tipo de colegio y "
                                    "factores del hogar, y ranking de municipios y colegios prioritarios."),
        ("Componente predictivo:", "clasificador de riesgo (puntaje global < percentil 25 nacional = 210) y "
                                   "regresor del puntaje global, usando solo variables conocidas antes de la "
                                   "prueba."),
        ("Entregable final:", "modelo empaquetado, API de inferencia con FastAPI [5] y tablero con Dash [6] "
                              "que consume la API, desplegados en contenedores Docker [7] en AWS."),
        ("Fuera del alcance:", "inferencia causal, diseño o evaluación de las intervenciones, datos "
                               "individuales no públicos y otras pruebas del ICFES."),
        ("Criterio de éxito:", "AUC ≥ 0,75 y recall ≥ 0,70 en la clase de riesgo sobre un conjunto de prueba "
                               "separado; tablero utilizable con filtros territoriales."),
    ])

    # III --------------------------------------------------------------------------------
    section_title(doc, "III", "Conjunto de datos")
    body(doc, "Se usa el conjunto «Resultados únicos Saber 11» publicado por el ICFES en datos.gov.co [1] (id "
              "kgxf-xxbe, API Socrata). Contiene un registro por estudiante evaluado desde 2010 con 51 columnas. "
              "Para esta entrega se toma el periodo más reciente publicado (20224): 1.065.888 filas "
              "descargadas, que corresponden a 532.788 estudiantes únicos, 10.378 colegios y 1.114 municipios. "
              "La descarga es reproducible con src/download_data.py, que selecciona 35 columnas vía SoQL. La "
              "Tabla I resume las variables.")
    table(doc, cnt, "Grupos de variables", ["Grupo", "Variables", "Uso"], [
        ["Estudiante", "género, edad (derivada), residencia", "Predictor"],
        ["Hogar", "estrato, educación madre y padre, personas, cuartos, internet, computador, "
                  "automóvil, lavadora", "Predictor"],
        ["Colegio", "naturaleza, zona, jornada, calendario, bilingüe, carácter, depto., municipio",
         "Predictor / filtro"],
        ["Resultados", "lectura, matemáticas, naturales, sociales, inglés (0–100), global (0–500)",
         "Objetivo"],
        ["Derivada", "riesgo = 1 si global < P25 (210)", "Objetivo"],
    ], widths=[1.6, 4.9, 1.9])
    body(doc, "El pipeline (src/clean_data.py) resuelve tres problemas. Primero, la fuente publica cada registro "
              "dos veces, lo que se verificó contra la API con count(distinct estu_consecutivo) = 532.792, y se "
              "deduplica por estudiante. Segundo, cuatro pruebas tienen puntaje 0 (anuladas) y se excluyen. "
              "Tercero, las variables del hogar tienen 4–7 % de nulos y cole_bilingue 18 %; se conservarán como "
              "categoría «Sin información».", lead="Calidad de datos.")

    # IV ---------------------------------------------------------------------------------
    section_title(doc, "IV", "Exploración de los datos")
    body(doc, "La exploración completa está en notebooks/01_eda.ipynb. Se presentan los resultados más "
              "relevantes para la pregunta de negocio.")
    subsection(doc, "A", "Variable objetivo")
    f = figure(doc, cnt, FIG / "02_dist_global.png",
               "Distribución del puntaje global con el umbral de riesgo P25 = 210 y la media.")
    body(doc, f"El puntaje global tiene media 250 y desviación estándar 52 (Fig. {f}). Su distribución es "
              "aproximadamente normal y ligeramente sesgada a la derecha. Definir el riesgo como el cuartil "
              "inferior genera una clase positiva del 25 %, un desbalance moderado: se evaluará con AUC y recall "
              "y se usará ponderación de clases. Los puntajes por área tienen correlaciones de 0,68 a 0,81 entre "
              "sí y casi determinan el global, por lo que no se usarán como predictores (fuga de información).")
    subsection(doc, "B", "Factores del hogar")
    f1 = figure(doc, cnt, FIG / "07_riesgo_edu_madre.png",
                "Tasa de riesgo por nivel educativo de la madre. Línea punteada: 25 % nacional.")
    f2 = figure(doc, cnt, FIG / "08_riesgo_recursos.png", "Tasa de riesgo según recursos del hogar.")
    body(doc, f"La educación de la madre es el factor con mayor asociación con el puntaje (η² = 0,13). El riesgo "
              f"baja de forma monótona de 55 % (sin educación) a 6 % (posgrado) (Fig. {f1}). Los estudiantes sin "
              f"internet o sin computador tienen aproximadamente el doble de riesgo (39 % y 34 %) que quienes sí "
              f"los tienen (19 % y 16 %) (Fig. {f2}). Esto apunta a intervenciones concretas, como la "
              "conectividad.")
    subsection(doc, "C", "Factores del colegio")
    f1 = figure(doc, cnt, FIG / "09_riesgo_colegio.png", "Tasa de riesgo según características del colegio.")
    f2 = figure(doc, cnt, FIG / "10_riesgo_jornada.png", "Tasa de riesgo por jornada escolar.")
    body(doc, f"Las jornadas nocturna y sabatina, que atienden principalmente a jóvenes en extraedad y adultos, "
              f"tienen más de 50 % de riesgo, frente a 12 % en la jornada completa (Fig. {f2}). Los colegios "
              f"rurales (40 %) y los oficiales (28 % vs. 16 %) también concentran el riesgo (Fig. {f1}). "
              "Calendario y bilingüismo casi no discriminan (η² ≈ 0).")
    subsection(doc, "D", "Dimensión territorial")
    f = figure(doc, cnt, FIG / "12_riesgo_depto.png", "Tasa de riesgo por departamento del colegio.")
    body(doc, f"La brecha territorial es muy marcada (Fig. {f}): Chocó (61 %), Vaupés (54 %), Amazonas (51 %) y "
              "La Guajira (47 %) frente a Boyacá y Bogotá (12 %). Dentro de los departamentos el riesgo se "
              "concentra aún más: 115 municipios con al menos 100 evaluados y 1.172 colegios tienen 50 % o más de "
              "estudiantes en riesgo (p. ej., Bojayá 98 % y Timbiquí 86 %). Por eso el tablero debe permitir "
              "bajar a nivel de municipio y colegio.")
    subsection(doc, "E", "Hallazgo de calidad: estrato")
    f = figure(doc, cnt, FIG / "11_heat_estrato_naturaleza.png",
               "Tasa de riesgo (%) por estrato y naturaleza del colegio.")
    body(doc, f"El riesgo por estrato no es monótono (Fig. {f}). En los colegios no oficiales baja con el "
              "estrato (46 % → 12 %), pero en los oficiales sube en los estratos 4–6 (40–64 %). Se verificó que no "
              "lo explican las jornadas de adultos ni la edad, por lo que se atribuye a errores de autorreporte. "
              "El estrato se usará junto con variables más confiables y no de forma aislada.")
    subsection(doc, "F", "Selección preliminar de variables")
    f = figure(doc, cnt, FIG / "14_eta2.png",
               "Proporción de la varianza del puntaje global explicada por cada variable (η²).")
    body(doc, f"Las variables con más poder explicativo (Fig. {f}) son la educación de los padres, la jornada, el "
              "acceso a computador e internet, el departamento y la naturaleza del colegio, que serán el núcleo "
              "del modelo. Género, calendario, bilingüismo y carácter aportan poco. Al combinar variables "
              "débilmente correlacionadas se espera superar el η² individual, lo que justifica un modelo "
              "multivariado: regresión logística como línea base y gradient boosting [4], con explicaciones "
              "SHAP [3].")

    # V ----------------------------------------------------------------------------------
    section_title(doc, "V", "Maqueta del prototipo")
    body(doc, "El tablero tiene tres pestañas. «Diagnóstico territorial» responde dónde y a quién intervenir con "
              "datos descriptivos. «Predicción de riesgo» consume el modelo a través de la API. «Priorización de "
              "colegios» permite cargar un listado por lotes y exportar la lista priorizada. Las cifras de la "
              "maqueta son reales (EDA); solo los valores del modelo (probabilidad y contribuciones SHAP) son "
              "ilustrativos.")
    body(doc, "La versión inicial (Semana 2) se ajustó con el EDA en cuatro puntos: (a) se agregó el filtro de "
              "jornada por su alto poder explicativo; (b) el formulario excluye los puntajes por área para evitar "
              "fuga de información; (c) se añadió el nivel municipal, porque el riesgo se concentra por debajo del "
              "nivel departamental; (d) se incluyó la matriz estrato × naturaleza para hacer visible la "
              "inconsistencia del estrato.", lead="Iteración según los datos.")
    new_section(doc, 1)
    figure(doc, cnt, MOCK / "mockup_diagnostico.png",
           "Vista 1, diagnóstico territorial: filtros (1), KPIs (2), riesgo por departamento (3), factores "
           "asociados (4), municipios prioritarios (5) e interacción estrato × naturaleza (6).", width=FULL_W)
    figure(doc, cnt, MOCK / "mockup_prediccion.png",
           "Vista 2, predicción: perfil del estudiante (7), probabilidad de riesgo y puntaje estimado (8), "
           "factores explicativos (9), contrato de la API (10) y predicción por lotes (11).", width=FULL_W)
    new_section(doc, 2)

    # VI ---------------------------------------------------------------------------------
    section_title(doc, "VI", "Repositorios de código y datos")
    body(doc, f"El código está en GitHub ({REPO_URL}). Los datos se versionan con DVC [2] en un remoto Amazon S3 "
              f"({S3_URL}). Git solo almacena los metadatos (dvc.yaml, dvc.lock y .dvc/config); los archivos de "
              "datos (CSV crudo de 292 MB y Parquet limpio de 15 MB) se suben con «dvc push». El pipeline DVC "
              "tiene dos etapas, download y clean, y se reproduce con «dvc repro». Cualquier integrante obtiene "
              "los datos con «dvc pull». La Tabla II resume la estructura del repositorio.")
    table(doc, cnt, "Estructura del repositorio", ["Ruta", "Contenido"], [
        ["src/download_data.py", "Descarga paginada desde la API Socrata"],
        ["src/clean_data.py", "Deduplicación, tipos, edad y variable objetivo"],
        ["dvc.yaml / dvc.lock", "Pipeline download → clean y hashes de datos"],
        ["notebooks/01_eda.ipynb", "Exploración de datos (14 figuras)"],
        ["mockup/", "Maqueta HTML del tablero y capturas"],
        ["docs/", "Reportes y script generador"],
    ], widths=[3.4, 5.0])
    body(doc, f"Las Figs. {cnt.fig + 1}–{cnt.fig + 3} evidencian el uso de ambos repositorios: los commits del "
              "proyecto, el almacenamiento de los datos en S3 y la sincronización entre la caché local y el "
              "remoto.")
    new_section(doc, 1)
    figure_pair(doc, cnt, (CAP / "github_commits.png", "Historial de commits en GitHub (rama main)."),
                (CAP / "s3_bucket.png", "Remoto DVC en Amazon S3: bucket mateorios2002-dvcstore, prefijo saber11/."))
    figure(doc, cnt, CAP / "dvc_push_status.png",
           "Sincronización de los datos con el remoto: «dvc push» y «dvc status -c».", width=FULL_W)
    new_section(doc, 2)

    # VII --------------------------------------------------------------------------------
    section_title(doc, "VII", "Conclusiones y trabajo futuro")
    body(doc, "Los datos abiertos del ICFES permiten responder la pregunta de negocio: el riesgo de bajo "
              "desempeño se concentra en perfiles del hogar, del colegio y del territorio identificables antes de "
              "la prueba, lo que justifica un modelo predictivo de focalización. Las siguientes entregas "
              "abordarán: (1) ampliar los datos a periodos anteriores para validar la estabilidad temporal; "
              "(2) entrenar la línea base y gradient boosting con seguimiento de experimentos en MLflow; y "
              "(3) construir la API y el tablero, contenerizarlos con Docker y desplegarlos en AWS.")

    references(doc, [
        "ICFES, “Resultados únicos Saber 11,” Datos Abiertos Colombia, 2024. [En línea]. Disponible: "
        "https://www.datos.gov.co/Educaci-n/Resultados-nicos-Saber-11/kgxf-xxbe",
        "Iterative, “DVC: Data Version Control.” [En línea]. Disponible: https://dvc.org",
        "S. M. Lundberg y S.-I. Lee, “A unified approach to interpreting model predictions,” en Proc. 31st "
        "Int. Conf. Neural Inf. Process. Syst. (NeurIPS), 2017, pp. 4765–4774.",
        "T. Chen y C. Guestrin, “XGBoost: A scalable tree boosting system,” en Proc. 22nd ACM SIGKDD Int. Conf. "
        "Knowl. Discov. Data Min., 2016, pp. 785–794.",
        "S. Ramírez, “FastAPI.” [En línea]. Disponible: https://fastapi.tiangolo.com",
        "Plotly Technologies Inc., “Dash.” [En línea]. Disponible: https://dash.plotly.com",
        "D. Merkel, “Docker: Lightweight Linux containers for consistent development and deployment,” "
        "Linux J., vol. 2014, no. 239, art. 2, 2014.",
    ])
    new_section(doc, 2)  # salto continuo final: equilibra las columnas de la última página

    out = OUT / "reporte_entrega1.docx"
    doc.save(out)
    print("Guardado", out)


# ----------------------------------------------------------------------------- reporte de equipo
def reporte_equipo():
    doc = base_doc()
    cnt = Counter()
    title_block(doc, "Reporte de Trabajo en Equipo",
                "Proyecto Monitor de Riesgo Académico Saber 11 — Entrega 1 · " + FECHA)
    body(doc, "El equipo definió los ítems de trabajo en la Semana 2, los repartió por afinidad y fijó revisiones "
              "internas antes de la entrega. Cada integrante sube su trabajo al repositorio con commits propios, "
              f"de modo que el historial de GitHub ({REPO_URL}) respalda la distribución de la Tabla I.")
    table(doc, cnt, "Responsabilidades individuales",
          ["Integrante", "Responsabilidades", "Evidencia en el repositorio"], [
              ["Mateo Ríos",
               "Coordinación del equipo y del cronograma. Configuración del repositorio Git y de DVC con remoto "
               "S3. Pipeline de datos (descarga desde la API Socrata, limpieza y variable objetivo). Integración "
               "y redacción del reporte.",
               "src/download_data.py, src/clean_data.py, dvc.yaml, dvc.lock, .dvc/config, README.md, docs/"],
              ["Harol Perafan",
               "Exploración de los factores socioeconómicos y del colegio (estrato, educación de los padres, "
               "recursos del hogar, naturaleza, zona, jornada). Análisis de la anomalía del estrato. Selección "
               "preliminar de variables (η²).",
               "notebooks/01_eda.ipynb (secciones 3, 4 y 6), reports/figures/05–11 y 14"],
              ["Sebastian Vivas",
               "Calidad de datos y distribución del puntaje. Exploración geográfica (departamentos, municipios "
               "y colegios prioritarios). Diseño de la maqueta del tablero y su iteración con los hallazgos del "
               "EDA.",
               "notebooks/01_eda.ipynb (secciones 1, 2 y 5), reports/figures/01–04 y 12–13, mockup/"],
          ], widths=[2.6, 8.6, 6.0], size=9)
    section_title(doc, None, "Actividades conjuntas")
    bullets(doc, [
        (None, "Selección del problema y de la pregunta de negocio entre las alternativas exploradas en la "
               "Semana 1."),
        (None, "Discusión de los hallazgos del EDA y de su impacto en el alcance, el modelo y la maqueta."),
        (None, "Revisión cruzada del reporte final antes de la entrega."),
    ])
    section_title(doc, None, "Reuniones de seguimiento")
    body(doc, f"El {FECHA} el equipo se reunió para revisar los resultados de la exploración de datos, validar "
              "la maqueta del tablero, confirmar la distribución de responsabilidades y aprobar el reporte final "
              "de la Entrega 1.", indent=False)
    out = OUT / "reporte_equipo.docx"
    doc.save(out)
    print("Guardado", out)


if __name__ == "__main__":
    reporte_entrega()
    reporte_equipo()
