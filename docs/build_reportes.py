"""Genera los reportes de la Entrega 1 (.docx) a partir de las figuras del EDA y la maqueta.

Uso: python docs/build_reportes.py
"""
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "reports" / "figures"
MOCK = ROOT / "mockup"
OUT = ROOT / "docs"

BLUE = RGBColor(0x0D, 0x36, 0x6B)
GREY = RGBColor(0x52, 0x51, 0x4E)

REPO_URL = "https://github.com/mateor0408-sys/proyecto-saber11-dsa"
S3_URL = "s3://mateorios2002-dvcstore/saber11"


def base_doc():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.59), Cm(27.94)
    for side in ("left_margin", "right_margin"):
        setattr(sec, side, Cm(2.2))
    sec.top_margin = sec.bottom_margin = Cm(2)
    st = doc.styles["Normal"]
    st.font.name, st.font.size = "Calibri", Pt(10.5)
    st.paragraph_format.space_after = Pt(4)
    st.paragraph_format.line_spacing = 1.08
    for name, size in (("Heading 1", 14), ("Heading 2", 11.5)):
        h = doc.styles[name]
        h.font.name, h.font.size, h.font.color.rgb, h.font.bold = "Calibri", Pt(size), BLUE, True
        h.paragraph_format.space_before = Pt(10)
        h.paragraph_format.space_after = Pt(4)
    return doc


def para(doc, text, bold_prefix=None, size=None, italic=False, align=None, color=None):
    p = doc.add_paragraph()
    if bold_prefix:
        p.add_run(bold_prefix).bold = True
    r = p.add_run(text)
    r.italic = italic
    if size:
        r.font.size = Pt(size)
    if color:
        r.font.color.rgb = color
    if align:
        p.alignment = align
    return p


def bullets(doc, items):
    for it in items:
        p = doc.add_paragraph(style="List Bullet")
        if isinstance(it, tuple):
            p.add_run(it[0]).bold = True
            p.add_run(it[1])
        else:
            p.add_run(it)
        p.paragraph_format.space_after = Pt(2)


def placeholder(p, text):
    r = p.add_run(text)
    r.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return r


def shade(cell, hex_color):
    tc = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tc.append(shd)


def table(doc, header, rows, widths, size=9):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold, r.font.size = True, Pt(size)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        shade(c, "0D366B")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            cells[i].paragraphs[0].add_run(str(v)).font.size = Pt(size)
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return t


def figure(doc, path, width_cm, caption):
    doc.add_picture(str(path), width=Cm(width_cm))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = para(doc, caption, size=8.5, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, color=GREY)
    p.paragraph_format.space_after = Pt(6)


def figure_pair(doc, left, right, caption, width_cm=8.3):
    t = doc.add_table(rows=1, cols=2)
    for cell, path in zip(t.rows[0].cells, (left, right)):
        cell.width = Cm(width_cm + 0.3)
        cell.paragraphs[0].add_run().add_picture(str(path), width=Cm(width_cm))
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = para(doc, caption, size=8.5, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, color=GREY)
    p.paragraph_format.space_after = Pt(6)


# --------------------------------------------------------------------------------------
def reporte_entrega():
    doc = base_doc()

    t = para(doc, "Monitor de Riesgo Académico Saber 11", size=20, color=BLUE)
    t.runs[0].bold = True
    para(doc, "Proyecto — Entrega 1 · Despliegue de Soluciones Analíticas (MIAD)", size=11, color=GREY)
    para(doc, "Equipo: Mateo Ríos · Harol Perafan · Sebastian Vivas   |   25 de octubre de 2026", size=10, color=GREY)
    p = para(doc, "Repositorio Git: ", size=10)
    p.add_run(REPO_URL)
    p.add_run("   ·   Remoto DVC: ").font.size = Pt(10)
    p.add_run(S3_URL)

    # 1 -------------------------------------------------------------------------------
    doc.add_heading("1. Problema y contexto", level=1)
    para(doc, "El examen Saber 11 del ICFES evalúa a todos los estudiantes que terminan la educación media en Colombia "
              "y su puntaje global (0–500) condiciona el acceso a la educación superior, a becas (p. ej. Generación E) y "
              "a créditos educativos. Los resultados muestran brechas persistentes asociadas al contexto del estudiante: "
              "en el periodo analizado, un estudiante de un colegio en Chocó tiene 5 veces más probabilidad de quedar en "
              "el cuartil inferior que uno de Bogotá (61 % vs 12 %).")
    para(doc, "Las secretarías de educación y los rectores cuentan con recursos limitados para programas de refuerzo "
              "(preparación pre-Saber, tutorías, conectividad). Hoy la focalización se hace con los resultados del año "
              "anterior, es decir, cuando el estudiante ya presentó la prueba. El problema es la falta de una herramienta "
              "que, con información disponible antes del examen (características del hogar y del colegio), identifique "
              "a tiempo a los estudiantes y colegios con mayor riesgo de bajo desempeño.")
    para(doc, "Un modelo supervisado entrenado con los resultados históricos permite estimar ese riesgo para cada "
              "estudiante de grado 11 al inicio del año escolar. Combinado con un tablero descriptivo, convierte los datos "
              "abiertos del ICFES en una lista priorizada y explicada de a quién y dónde intervenir.",
         bold_prefix="Por qué un modelo es útil: ")

    # 2 -------------------------------------------------------------------------------
    doc.add_heading("2. Pregunta de negocio y alcance", level=1)
    p = para(doc, "¿Qué estudiantes (y colegios/municipios) tienen mayor riesgo de obtener un puntaje global bajo en "
                  "Saber 11, dadas sus características socioeconómicas y del colegio, para priorizar intervenciones de "
                  "refuerzo?", italic=True)
    p.runs[0].bold = True
    bullets(doc, [
        ("Usuarios: ", "secretarías de educación departamentales/municipales y rectores de colegios."),
        ("Componente descriptivo: ", "tablero con la distribución del riesgo por territorio, tipo de colegio y "
                                     "factores del hogar, y ranking de municipios/colegios prioritarios."),
        ("Componente predictivo: ", "(i) clasificador de riesgo, definido como puntaje global < percentil 25 "
                                    "nacional (210 puntos); (ii) regresor del puntaje global como complemento. "
                                    "Solo con variables conocidas antes de la prueba."),
        ("Entregable final: ", "modelo empaquetado, API de inferencia (FastAPI) y tablero (Dash) que consume la API, "
                               "desplegados en contenedores Docker en AWS."),
        ("Fuera del alcance: ", "inferencia causal, diseño o evaluación de las intervenciones, datos individuales "
                                "no públicos (notas, asistencia) y otras pruebas (Saber 3°, 5°, 9°, Pro)."),
        ("Criterio de éxito: ", "AUC ≥ 0,75 y recall ≥ 0,70 en la clase de riesgo sobre un conjunto de prueba "
                                "separado; tablero utilizable con filtros por territorio."),
    ])

    # 3 -------------------------------------------------------------------------------
    doc.add_heading("3. Conjunto de datos", level=1)
    para(doc, "Se usa el conjunto «Resultados únicos Saber 11» publicado por el ICFES en el portal de datos abiertos "
              "datos.gov.co (id kgxf-xxbe, API Socrata). Contiene un registro por estudiante evaluado desde 2010 con "
              "51 columnas. Para esta entrega se toma el periodo más reciente publicado (20224, calendario A y B): "
              "1.065.888 filas descargadas, que corresponden a 532.788 estudiantes únicos, 10.378 colegios y 1.114 "
              "municipios. La descarga es reproducible mediante el script src/download_data.py, que selecciona 35 "
              "columnas relevantes vía SoQL.")
    table(doc, ["Grupo", "Variables (ejemplos)", "Uso"], [
        ["Estudiante", "estu_genero, edad (derivada de la fecha de nacimiento), depto/municipio de residencia", "Predictor"],
        ["Hogar (fami_*)", "estrato, educación de madre y padre, personas y cuartos del hogar, internet, computador, "
                           "automóvil, lavadora", "Predictor"],
        ["Colegio (cole_*)", "naturaleza (oficial/no oficial), zona, jornada, calendario, bilingüe, carácter, "
                             "género, departamento y municipio, código DANE", "Predictor / filtro"],
        ["Resultados (punt_*)", "lectura crítica, matemáticas, c. naturales, sociales, inglés (0–100), global (0–500)",
         "Objetivo / descriptivo"],
        ["Derivada", "riesgo_bajo_desempeno = 1 si punt_global < P25 (210)", "Objetivo"],
    ], widths=[3.2, 10.3, 3.5])
    para(doc, "Se encontraron tres problemas de calidad que el pipeline (src/clean_data.py) resuelve: "
              "(1) la fuente publica cada registro dos veces, lo que se verificó contra la API con count(distinct "
              "estu_consecutivo) = 532.792, y se deduplica por estudiante; (2) cuatro pruebas tienen puntaje global 0 "
              "(anuladas) y se excluyen; (3) las variables del hogar tienen 4–7 % de nulos y cole_bilingue 18 %. Estos "
              "nulos se conservan para imputarlos como categoría «Sin información» en el modelado (Figura 1).",
         bold_prefix="Calidad de datos. ")

    # 4 -------------------------------------------------------------------------------
    doc.add_heading("4. Exploración de los datos", level=1)
    para(doc, "La exploración completa está en notebooks/01_eda.ipynb. Se presentan los resultados más relevantes "
              "para la pregunta de negocio.")
    figure_pair(doc, FIG / "01_nulos.png", FIG / "02_dist_global.png",
                "Figura 1. Variables con datos faltantes (izq.) y distribución del puntaje global con el umbral de "
                "riesgo P25 = 210 (der.).")
    para(doc, "El puntaje global tiene media 250 y desviación estándar 52, con una distribución aproximadamente normal "
              "y ligeramente sesgada a la derecha (máx. 477). Definir el riesgo como el cuartil inferior genera una "
              "clase positiva del 25 %. El desbalance es moderado, por lo que se evaluará con AUC y recall y se usará "
              "ponderación de clases. Los cinco puntajes por área tienen correlaciones de 0,68 a 0,81 con los demás "
              "y casi determinan el global, así que no se usarán como predictores: serían fuga de información.",
         bold_prefix="Variable objetivo. ")
    figure_pair(doc, FIG / "07_riesgo_edu_madre.png", FIG / "08_riesgo_recursos.png",
                "Figura 2. Tasa de riesgo por nivel educativo de la madre (izq.) y por recursos del hogar (der.). "
                "Línea punteada = 25 % nacional.")
    para(doc, "La educación de la madre es el factor con mayor asociación con el puntaje (η² = 0,13). El riesgo baja "
              "de forma monótona de 55 % (sin educación) a 6 % (posgrado). Los estudiantes sin internet o sin "
              "computador en casa tienen aproximadamente el doble de riesgo (39 % y 34 %) que quienes sí los tienen "
              "(19 % y 16 %). Estas variables son buenas candidatas para el modelo y apuntan a intervenciones "
              "concretas, como la conectividad.",
         bold_prefix="Factores del hogar. ")
    figure_pair(doc, FIG / "09_riesgo_colegio.png", FIG / "10_riesgo_jornada.png",
                "Figura 3. Tasa de riesgo según características del colegio (izq.) y jornada (der.).")
    para(doc, "Las jornadas nocturna y sabatina, que atienden principalmente a jóvenes en extraedad y adultos, tienen "
              "más de 50 % de riesgo, frente a 12 % en la jornada completa. Los colegios rurales (40 %) y los oficiales "
              "(28 % vs 16 % en los no oficiales) también concentran el riesgo. Calendario y bilingüismo casi no "
              "discriminan (η² ≈ 0).",
         bold_prefix="Factores del colegio. ")
    figure_pair(doc, FIG / "12_riesgo_depto.png", FIG / "11_heat_estrato_naturaleza.png",
                "Figura 4. Tasa de riesgo por departamento (izq.) y por estrato × naturaleza del colegio (der.).",
                width_cm=8.0)
    para(doc, "La brecha territorial es muy marcada: Chocó (61 %), Vaupés (54 %), Amazonas (51 %) y La Guajira (47 %) "
              "frente a Boyacá (12 %) y Bogotá (12 %). Dentro de los departamentos el riesgo se concentra aún más: 115 "
              "municipios con al menos 100 evaluados y 1.172 colegios tienen 50 % o más de estudiantes en riesgo (p. ej. "
              "Bojayá 98 % y Timbiquí 86 %). Por eso el tablero debe permitir bajar a nivel de municipio y colegio.",
         bold_prefix="Territorio. ")
    para(doc, "El riesgo por estrato no es monótono. En los colegios no oficiales baja con el estrato, como se espera "
              "(46 % → 12 %), pero en los oficiales sube en los estratos 4–6 (40–64 %). Se verificó que la anomalía no "
              "la explican las jornadas de adultos ni la edad, por lo que se atribuye a errores de autorreporte. El "
              "estrato se usará junto con variables más confiables y no de forma aislada.",
         bold_prefix="Hallazgo de calidad. ")
    figure(doc, FIG / "14_eta2.png", 11.5,
           "Figura 5. Proporción de la varianza del puntaje global explicada por cada variable (η²).")
    para(doc, "Las variables con más poder explicativo son la educación de los padres, la jornada, el acceso a "
              "computador e internet, el departamento y la naturaleza del colegio. Serán el núcleo del modelo. Género, "
              "calendario, bilingüismo y carácter aportan poco. Al combinar varias variables débilmente correlacionadas "
              "se espera superar el η² individual, lo que justifica un modelo multivariado (regresión logística como "
              "línea base y gradient boosting).",
         bold_prefix="Selección preliminar de variables. ")

    # 5 -------------------------------------------------------------------------------
    doc.add_heading("5. Maqueta del prototipo", level=1)
    para(doc, "El tablero tiene tres pestañas. Diagnóstico territorial responde dónde y a quién intervenir con datos "
              "descriptivos. Predicción de riesgo consume el modelo a través de la API. Priorización de colegios "
              "permite cargar un listado por lotes y exportar la lista priorizada. Los números de la maqueta son "
              "cifras reales del EDA; solo los valores del modelo (probabilidad y contribuciones SHAP) son "
              "ilustrativos.")
    figure(doc, MOCK / "mockup_diagnostico.png", 16.5,
           "Figura 6. Vista 1 — Diagnóstico territorial: filtros (1), KPIs (2), riesgo por departamento (3), "
           "factores asociados (4), municipios prioritarios (5) e interacción estrato × naturaleza (6).")
    figure(doc, MOCK / "mockup_prediccion.png", 16.5,
           "Figura 7. Vista 2 — Predicción: perfil del estudiante (7), probabilidad de riesgo y puntaje estimado "
           "(8), factores explicativos (9), contrato de la API (10) y predicción por lotes (11).")
    para(doc, "La versión inicial de la maqueta (Semana 2) se ajustó con los hallazgos del EDA en cuatro puntos. "
              "(a) Se agregó el filtro de jornada y se resaltó en los factores, por su alto poder explicativo. "
              "(b) El formulario de predicción excluye los puntajes por área para evitar fuga de información. "
              "(c) Se añadió el nivel municipal y la lista de municipios prioritarios, porque el riesgo se concentra "
              "por debajo del nivel departamental. (d) Se incluyó la matriz estrato × naturaleza para hacer visible la "
              "inconsistencia del estrato.",
         bold_prefix="Iteración según los datos. ")

    # 6 -------------------------------------------------------------------------------
    doc.add_heading("6. Repositorios de código (Git) y datos (DVC)", level=1)
    p = para(doc, "Código en GitHub: ")
    p.add_run(REPO_URL)
    p.add_run(". Datos versionados con DVC en un remoto S3 (")
    p.add_run(S3_URL)
    p.add_run("). Git solo almacena los metadatos (dvc.yaml, dvc.lock, .dvc/config); los archivos de datos "
              "(data/raw/saber11.csv de 292 MB y data/processed/saber11_clean.parquet de 15 MB) se suben con dvc push. "
              "El pipeline DVC tiene dos etapas, download y clean, y se reproduce con «dvc repro». Cualquier integrante "
              "obtiene los datos con «dvc pull».")
    table(doc, ["Ruta", "Contenido"], [
        ["src/download_data.py", "Descarga paginada desde la API Socrata con reintentos"],
        ["src/clean_data.py", "Deduplicación, tipos, edad, normalización y variable objetivo"],
        ["dvc.yaml / dvc.lock", "Pipeline download → clean y hashes de los datos versionados"],
        ["notebooks/01_eda.ipynb", "Exploración de datos (14 figuras en reports/figures/)"],
        ["mockup/", "Maqueta HTML del tablero y capturas"],
        ["docs/", "Reportes de la entrega y su script generador"],
    ], widths=[5, 12])
    p = para(doc, "")
    placeholder(p, "[Insertar capturas: (1) historial de commits en GitHub con los tres integrantes; "
                   "(2) salida de «dvc push» / «dvc status -c»; (3) bucket S3 con los archivos de DVC.]")

    # 7 -------------------------------------------------------------------------------
    doc.add_heading("7. Próximos pasos", level=1)
    bullets(doc, [
        "Ampliar los datos a periodos anteriores (20194) para validar la estabilidad temporal del modelo.",
        "Entrenar la línea base (regresión logística) y gradient boosting con seguimiento de experimentos en MLflow.",
        "Construir la API (FastAPI) y el tablero (Dash), contenerizarlos con Docker y desplegarlos en AWS.",
    ])

    out = OUT / "reporte_entrega1.docx"
    doc.save(out)
    print("Guardado", out)


# --------------------------------------------------------------------------------------
def reporte_equipo():
    doc = base_doc()
    t = para(doc, "Reporte de trabajo en equipo — Entrega 1", size=16, color=BLUE)
    t.runs[0].bold = True
    para(doc, "Proyecto: Monitor de Riesgo Académico Saber 11 · Despliegue de Soluciones Analíticas (MIAD) · "
              "25 de octubre de 2026", size=10, color=GREY)
    para(doc, "El equipo definió los ítems de trabajo en la Semana 2, los repartió por afinidad y fijó revisiones "
              "internas antes de cada entrega. Cada integrante sube su trabajo al repositorio con commits propios, así "
              "que el historial de GitHub respalda esta distribución.")
    table(doc, ["Integrante", "Responsabilidades", "Evidencia en el repositorio"], [
        ["Mateo Ríos",
         "Coordinación del equipo y del cronograma. Configuración del repositorio Git y de DVC con remoto S3. "
         "Pipeline de datos (descarga desde la API Socrata, limpieza y variable objetivo). Integración y redacción "
         "del reporte.",
         "src/download_data.py, src/clean_data.py, dvc.yaml, dvc.lock, .dvc/config, README.md, docs/"],
        ["Harol Perafan",
         "Exploración de los factores socioeconómicos y del colegio (estrato, educación de los padres, recursos del "
         "hogar, naturaleza, zona, jornada). Análisis de la anomalía del estrato. Selección preliminar de "
         "variables (η²).",
         "notebooks/01_eda.ipynb (secciones 3, 4 y 6), reports/figures/05–11, 14"],
        ["Sebastian Vivas",
         "Calidad de datos y distribución del puntaje. Exploración geográfica (departamentos, municipios y "
         "colegios prioritarios). Diseño de la maqueta del tablero y su iteración con los hallazgos del EDA.",
         "notebooks/01_eda.ipynb (secciones 1, 2 y 5), reports/figures/01–04, 12–13, mockup/"],
    ], widths=[3.0, 8.4, 5.6], size=9.5)
    para(doc, "Actividades conjuntas: ", bold_prefix=None).runs[0].bold = True
    bullets(doc, [
        "Selección del problema y de la pregunta de negocio entre las alternativas exploradas en la Semana 1.",
        "Discusión de los hallazgos del EDA y de su impacto en el alcance, el modelo y la maqueta.",
        "Revisión cruzada del reporte final antes de la entrega.",
    ])
    p = para(doc, "")
    placeholder(p, "[Ajustar la distribución si difiere de lo realizado y agregar fechas de las reuniones de "
                   "seguimiento.]")
    out = OUT / "reporte_equipo.docx"
    doc.save(out)
    print("Guardado", out)


if __name__ == "__main__":
    reporte_entrega()
    reporte_equipo()
