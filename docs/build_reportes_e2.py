"""Genera los reportes de la Entrega 2 (.docx, formato IEEE).

Las cifras se leen de los resultados exportados de MLflow (reports/modelos/*.csv, models/seleccion.json),
por lo que el texto se mantiene consistente con los experimentos.
Uso: python docs/build_reportes_e2.py
"""
import json

import pandas as pd
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.shared import Pt

from build_reportes import (COL_W, FULL_W, OUT, REPO_URL, ROOT, Counter, base_doc, body, bullets,
                            figure, figure_pair, new_section, references, section_title, set_font,
                            subsection, table, title_block)

FECHA = "8 de noviembre de 2026"
MLFLOW_IP = "54.242.29.105"
MOD = ROOT / "reports" / "modelos"
TAB = ROOT / "reports" / "tablero"
CAP = ROOT / "reports" / "capturas_e2"

CLF = pd.read_csv(MOD / "clasificacion.csv")
REG = pd.read_csv(MOD / "regresion.csv")
SEL = json.loads((ROOT / "models" / "seleccion.json").read_text())
BEST, BEST_REG = SEL["riesgo"], SEL["puntaje"]
M, MR = BEST["metricas"], BEST_REG["metricas"]


def c(x, d=3):
    """Número con coma decimal."""
    return f"{x:.{d}f}".replace(".", ",")


def run(name):
    return CLF.set_index("run").loc[name]


def placeholder(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    set_font(r, size=9)
    r.font.highlight_color = WD_COLOR_INDEX.YELLOW


def capture(doc, cnt, name, caption, width=COL_W):
    path = CAP / name
    if path.exists():
        return figure(doc, cnt, path, caption, width=width)
    placeholder(doc, f"[Captura pendiente: reports/capturas_e2/{name} — {caption}]")
    return None


# ----------------------------------------------------------------------------- reporte principal
def reporte_entrega():
    doc = base_doc()
    cnt = Counter()
    title_block(doc, "Monitor de Riesgo Académico Saber 11: Modelos y Tablero",
                "Proyecto — Entrega 2 · Despliegue de Soluciones Analíticas · " + FECHA)
    new_section(doc, 2)

    lin, rf = run("logreg-base"), run("rf-d20-bal")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    set_font(p.add_run("Resumen—"), size=9, bold=True, italic=True)
    set_font(p.add_run(
        f"Se entrenaron y compararon {len(CLF)} modelos de clasificación del riesgo de bajo desempeño en Saber 11 "
        f"y {len(REG)} modelos de regresión del puntaje global, registrados en un servidor MLflow desplegado en "
        f"AWS EC2. El mejor modelo, un gradient boosting basado en histogramas, alcanza AUC-ROC de "
        f"{c(M['test_auc_roc'])} y AUC-PR de {c(M['test_auc_pr'])} en el conjunto de prueba; con un umbral elegido "
        f"para detectar al menos 70 % de los estudiantes en riesgo, su precisión es {c(M['test_precision'], 2)}, "
        f"{c(M['test_precision'] / 0.25, 1)} veces la tasa base. El modelo se integró en un tablero Dash con "
        "diagnóstico territorial, predicción individual explicada y priorización por lotes."), size=9, bold=True)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(4), Pt(2)
    set_font(p.add_run("Palabras clave—"), size=9, bold=True, italic=True)
    set_font(p.add_run("Saber 11, riesgo académico, gradient boosting, MLflow, AWS EC2, tablero Dash."),
             size=9, bold=True)

    # I -------------------------------------------------------------------------------------------
    section_title(doc, "I", "Resumen del problema")
    body(doc, "El puntaje global de Saber 11 (0–500) condiciona el acceso a la educación superior y a becas, y "
              "presenta brechas marcadas por territorio y contexto socioeconómico (p. ej., 61 % de estudiantes en "
              "el cuartil inferior en Chocó frente a 12 % en Bogotá). Las secretarías de educación focalizan hoy "
              "sus programas de refuerzo con resultados del año anterior, cuando el estudiante ya presentó la "
              "prueba.", lead="Contexto.")
    body(doc, "¿Qué estudiantes (y colegios/municipios) tienen mayor riesgo de obtener un puntaje global bajo "
              "(< 210, percentil 25 nacional), dadas sus características socioeconómicas y del colegio, para "
              "priorizar intervenciones de refuerzo? El alcance es un prototipo con modelos supervisados, una "
              "API de inferencia y un tablero, desplegados con Docker en AWS.", lead="Pregunta de negocio y alcance.")
    body(doc, "Resultados únicos Saber 11 del ICFES (datos.gov.co, id kgxf-xxbe) [1], periodo 20224: "
              "532.788 estudiantes únicos, 10.378 colegios, versionados con DVC en S3.", lead="Datos.")
    body(doc, "", lead="Cambios respecto a la Entrega 1.")
    bullets(doc, [
        ("Integración modelo–tablero:", "en esta entrega el tablero carga el modelo empaquetado exportado desde "
                                        "MLflow; la API FastAPI y los contenedores Docker se abordan en la "
                                        "Entrega 3."),
        ("Variables:", "se fijó un conjunto de 19 variables previas a la prueba; la edad, no destacada en E1, "
                       "resultó la segunda más importante (captura la extraedad)."),
        ("Umbral de decisión:", f"se calibró en {c(M['umbral'], 2)} sobre validación para cumplir el criterio de "
                                "recall ≥ 0,70 definido en E1."),
        ("Tablero:", "la pestaña «Priorización de colegios» pasó a «Priorización por lotes» (CSV) y el ranking de "
                     "colegios se integró al diagnóstico al filtrar un municipio."),
    ])

    # II ------------------------------------------------------------------------------------------
    section_title(doc, "II", "Desarrollo de los modelos")
    subsection(doc, "A", "Variables y selección de características")
    body(doc, "Se usan solo variables conocidas antes de la prueba (src/features.py): nueve del hogar (educación "
              "de madre y padre, estrato, internet, computador, automóvil, lavadora, personas y cuartos), ocho del "
              "colegio (naturaleza, zona, jornada, calendario, bilingüismo, carácter, género y departamento), el "
              "género y la edad del estudiante. Los puntajes por área se excluyen porque determinan el puntaje "
              "global (fuga de información). La selección se apoyó en el η² del EDA y se validó con una ablación "
              "que entrena el mejor algoritmo solo con variables del hogar o solo del colegio.")
    subsection(doc, "B", "Preprocesamiento y protocolo")
    body(doc, "Los nulos categóricos (4–18 %) se codifican como la categoría «Sin información» y la edad se imputa "
              "con la mediana. Los modelos lineales usan one-hot y los de árboles codificación ordinal; el "
              "gradient boosting usa además el soporte nativo de variables categóricas. Los datos se dividen de "
              "forma estratificada en entrenamiento (70 %), validación (15 %) y prueba (15 %) con semilla fija. "
              "La selección de modelos usa solo validación: el criterio principal es el AUC-PR, más informativo "
              "que el AUC-ROC con clases desbalanceadas [7], y el umbral se elige como el mayor valor con "
              "recall ≥ 0,70 en validación.")
    subsection(doc, "C", "Algoritmos y experimentos")
    body(doc, "Se evaluaron regresión logística (con y sin ponderación de clases y dos niveles de regularización), "
              "bosque aleatorio [5] y gradient boosting basado en histogramas de scikit-learn [3], inspirado en "
              "LightGBM [4], con varias configuraciones de tasa de aprendizaje, iteraciones y hojas. Para el puntaje "
              "global se comparó Ridge con gradient boosting de regresión. La Tabla I resume los experimentos.")
    table(doc, cnt, "Experimentos registrados en MLflow", ["Run", "Algoritmo y parámetros"], [
        ["logreg-base", "Reg. logística, C = 1"],
        ["logreg-C0.1-bal / C1-bal", "Reg. logística, class_weight = balanced, C ∈ {0,1; 1}"],
        ["rf-d14", "Bosque, 100 árboles, prof. 14, 30 % de muestra"],
        ["rf-d20-bal", "Bosque, prof. 20, hoja ≥ 10, balanceado"],
        ["hgb-lr0.1", "Gradient boosting, lr = 0,1, 200 iteraciones"],
        ["hgb-lr0.05-l63(-bal)", "lr = 0,05, 500 iter., 63 hojas (± balanceo)"],
        ["hgb-solo-hogar / colegio", "Ablación de variables con hgb-lr0.05-l63"],
        ["ridge-a1 / hgbr-*", "Regresión del puntaje global"],
    ], widths=[3.3, 5.1])
    subsection(doc, "D", "Seguimiento con MLflow")
    body(doc, f"Cada ejecución de src/train.py crea un run en un servidor MLflow [2] en una instancia EC2 "
              f"(http://{MLFLOW_IP}:5000) con backend SQLite y almacenamiento de artefactos. Por run se registran "
              "parámetros, métricas de validación y prueba, curvas ROC/PR, matriz de confusión, importancia por "
              "permutación y el modelo con su firma. src/select_best.py registra el mejor run de cada experimento en "
              "el Model Registry (alias «champion») y lo exporta a models/, versionado con DVC.")

    # III -----------------------------------------------------------------------------------------
    section_title(doc, "III", "Evaluación de los modelos")
    top = CLF.sort_values("val_auc_pr", ascending=False)
    table(doc, cnt, "Clasificación: métricas en validación", ["Run", "AUC-ROC", "AUC-PR", "Precisión*"],
          [[r.run, c(r.val_auc_roc), c(r.val_auc_pr), c(r.val_precision)] for r in top.itertuples()],
          widths=[3.6, 1.6, 1.6, 1.6])
    p = doc.add_paragraph()
    set_font(p.add_run("* Precisión con el umbral que garantiza recall ≥ 0,70."), size=8, italic=True)
    f_cmp = figure(doc, cnt, MOD / "comparacion_clasificacion.png",
                   "Comparación de los modelos de clasificación en validación (generada desde MLflow).")
    best_name = BEST["run_name"]
    body(doc, f"El gradient boosting domina (Tabla II, Fig. {f_cmp}): {best_name} obtiene AUC-PR de "
              f"{c(run(best_name).val_auc_pr)} frente a {c(rf.val_auc_pr)} del mejor bosque y {c(lin.val_auc_pr)} "
              "de la regresión logística. Se seleccionó como campeón y se evaluó en prueba (Tabla III).")
    f_roc = figure(doc, cnt, MOD / "mejor_riesgo_curvas_roc_pr.png",
                   f"Curvas ROC y precisión–recall del modelo campeón ({best_name}) en validación; el punto naranja "
                   "marca el umbral de decisión.")
    f_cm = figure(doc, cnt, MOD / "mejor_riesgo_matriz_confusion.png",
                  "Matriz de confusión del modelo campeón con el umbral de decisión (validación).")
    table(doc, cnt, "Modelos campeones en el conjunto de prueba", ["Modelo", "Métrica", "Valor"], [
        [best_name, "AUC-ROC / AUC-PR", f"{c(M['test_auc_roc'])} / {c(M['test_auc_pr'])}"],
        ["", "Recall / Precisión / F1", f"{c(M['test_recall'], 2)} / {c(M['test_precision'], 2)} / {c(M['test_f1'], 2)}"],
        ["", "Umbral", c(M["umbral"], 2)],
        [BEST_REG["run_name"], "RMSE / MAE (puntos)", f"{c(MR['test_rmse'], 1)} / {c(MR['test_mae'], 1)}"],
        ["", "R²", c(MR["test_r2"], 2)],
    ], widths=[2.9, 3.0, 2.5])
    f_imp = figure(doc, cnt, MOD / "mejor_riesgo_importancia_permutacion.png",
                   "Importancia por permutación (caída del AUC-PR) del modelo campeón.")
    reg_tbl = REG.sort_values("val_rmse")
    table(doc, cnt, "Regresión del puntaje global (validación)", ["Run", "RMSE", "MAE", "R²"],
          [[r.run, c(r.val_rmse, 1), c(r.val_mae, 1), c(r.val_r2, 3)] for r in reg_tbl.itertuples()],
          widths=[3.6, 1.6, 1.6, 1.6])

    # IV ------------------------------------------------------------------------------------------
    section_title(doc, "IV", "Observaciones y conclusiones")
    hgb = CLF[CLF.run.str.startswith("hgb-lr")]
    hog, col = run("hgb-solo-hogar"), run("hgb-solo-colegio")
    bullets(doc, [
        ("Algoritmo:", f"el boosting supera a los modelos lineales y al bosque en ≈ 0,02 de AUC-ROC y ≈ 0,04 de "
                       f"AUC-PR, porque captura interacciones (p. ej., departamento × zona × jornada). Entre sus "
                       f"configuraciones la diferencia de AUC-PR es de apenas "
                       f"{c(hgb.val_auc_pr.max() - hgb.val_auc_pr.min(), 4)}: "
                       "el desempeño está limitado por la información de las variables, no por la capacidad del "
                       "modelo."),
        ("Desbalance:", "ponderar las clases no cambia el AUC (la capacidad de ordenar estudiantes) y solo desplaza "
                        "el umbral; ajustar el umbral en validación es suficiente y más transparente."),
        ("Selección de variables:", f"con solo variables del hogar el AUC-ROC cae a {c(hog.val_auc_roc)} y con solo "
                                    f"variables del colegio a {c(col.val_auc_roc)}, frente a "
                                    f"{c(run(best_name).val_auc_roc)} con todas: ambos grupos son complementarios "
                                    f"(Fig. {f_cmp})."),
        ("Factores:", f"departamento, edad y jornada dominan la importancia (Fig. {f_imp}). La edad captura la "
                      "extraedad, coherente con el alto riesgo de las jornadas nocturna y sabatina del EDA. La "
                      "educación de la madre pierde peso individual porque comparte información con estrato, "
                      "cuartos y recursos del hogar."),
        ("Generalización:", f"las métricas de prueba (AUC-ROC {c(M['test_auc_roc'])}) son prácticamente iguales a "
                            f"las de validación ({c(run(best_name).val_auc_roc)}), sin señales de sobreajuste."),
        ("Valor operativo:", f"con recall {c(M['test_recall'], 2)}, de cada 100 estudiantes priorizados "
                             f"≈ {round(M['test_precision'] * 100)} están realmente en riesgo, frente a 25 si se "
                             f"eligieran al azar ({c(M['test_precision'] / 0.25, 1)}× más eficiente) (Figs. "
                             f"{f_roc}–{f_cm}). El criterio de éxito de E1 (AUC ≥ 0,75 y recall ≥ 0,70) se cumple."),
        ("Puntaje estimado:", f"el regresor explica {c(MR['test_r2'] * 100, 0)} % de la varianza (RMSE "
                              f"{c(MR['test_rmse'], 1)}); es un complemento orientativo y la decisión se basa en la "
                              "probabilidad de riesgo."),
        ("Limitaciones:", "un solo periodo (20224), estrato autorreportado y variables sensibles (departamento, "
                          "género): el modelo debe usarse para priorizar apoyo, no para etiquetar estudiantes. Se "
                          "validará la estabilidad temporal con el periodo 20194 en la siguiente entrega."),
    ])

    # V -------------------------------------------------------------------------------------------
    section_title(doc, "V", "Tablero desarrollado")
    body(doc, "El tablero (dashboard/app.py, Dash [6]) sigue la maqueta de la Entrega 1 y responde la pregunta de "
              "negocio en tres pestañas. (1) Diagnóstico territorial: filtros por departamento, municipio, "
              "naturaleza, zona y jornada; KPIs; tasa de riesgo por departamento (un clic filtra y baja a "
              "municipios); factores con selector de variable; tabla de municipios o colegios prioritarios; y la "
              "matriz estrato × naturaleza. (2) Predicción de riesgo: un formulario con el perfil del estudiante "
              "devuelve la probabilidad, el nivel (bajo/medio/alto), el puntaje estimado, la tasa de su "
              "departamento, una recomendación y los factores que más pesan, calculados por oclusión frente al "
              "perfil más común; incluye las métricas del modelo registrado. (3) Priorización por lotes: se carga "
              "un CSV de estudiantes, se obtiene la lista ordenada por riesgo y se descarga el resultado.")
    new_section(doc, 1)
    figure(doc, cnt, TAB / "tab1_diagnostico.png", "Pestaña 1 — Diagnóstico territorial.", width=FULL_W)
    figure_pair(doc, cnt, (TAB / "tab2_prediccion.png", "Pestaña 2 — Predicción de riesgo con factores "
                                                       "explicativos y métricas del modelo."),
                (TAB / "tab3_lotes.png", "Pestaña 3 — Priorización por lotes (modo demostración con 25 "
                                         "estudiantes)."))
    new_section(doc, 2)

    # VI ------------------------------------------------------------------------------------------
    section_title(doc, "VI", "Repositorio y evidencia de MLflow en EC2")
    body(doc, f"El código está en {REPO_URL}: modelos (src/features.py, train.py, run_experiments.sh, "
              "select_best.py, report_models.py), tablero (dashboard/), despliegue de MLflow (deploy/) y reportes "
              f"(docs/). El servidor MLflow corre en la instancia EC2 con IP pública {MLFLOW_IP} (puerto 5000). "
              "Las capturas evidencian la instancia y los experimentos registrados.")
    new_section(doc, 1)
    capture(doc, cnt, "ec2_instancia.png", f"Instancia EC2 en ejecución (IP {MLFLOW_IP}, usuario visible).",
            width=FULL_W)
    capture(doc, cnt, "mlflow_experimentos.png", f"Runs del experimento saber11-riesgo en MLflow "
                                                 f"(http://{MLFLOW_IP}:5000); el campeón figura como modelo registrado saber11-riesgo v1.",
            width=FULL_W)
    capture(doc, cnt, "mlflow_registro.png", "Experimentos de clasificación (saber11-riesgo) y regresión "
                                           "(saber11-puntaje) en el servidor MLflow.", width=FULL_W)
    new_section(doc, 2)

    references(doc, [
        "ICFES, “Resultados únicos Saber 11,” Datos Abiertos Colombia, 2024. [En línea]. Disponible: "
        "https://www.datos.gov.co/Educaci-n/Resultados-nicos-Saber-11/kgxf-xxbe",
        "M. Zaharia et al., “Accelerating the machine learning lifecycle with MLflow,” IEEE Data Eng. Bull., "
        "vol. 41, no. 4, pp. 39–45, 2018.",
        "F. Pedregosa et al., “Scikit-learn: Machine learning in Python,” J. Mach. Learn. Res., vol. 12, "
        "pp. 2825–2830, 2011.",
        "G. Ke et al., “LightGBM: A highly efficient gradient boosting decision tree,” en Proc. 31st Int. Conf. "
        "Neural Inf. Process. Syst. (NeurIPS), 2017, pp. 3146–3154.",
        "L. Breiman, “Random forests,” Mach. Learn., vol. 45, no. 1, pp. 5–32, 2001.",
        "Plotly Technologies Inc., “Dash.” [En línea]. Disponible: https://dash.plotly.com",
        "T. Saito y M. Rehmsmeier, “The precision-recall plot is more informative than the ROC plot when "
        "evaluating binary classifiers on imbalanced datasets,” PLoS ONE, vol. 10, no. 3, e0118432, 2015.",
    ])
    new_section(doc, 2)
    out = OUT / "reporte_entrega2.docx"
    doc.save(out)
    print("Guardado", out)


# ----------------------------------------------------------------------------- reporte de equipo
def reporte_equipo():
    doc = base_doc()
    cnt = Counter()
    title_block(doc, "Reporte de Trabajo en Equipo",
                "Proyecto Monitor de Riesgo Académico Saber 11 — Entrega 2 · " + FECHA)
    body(doc, "El equipo distribuyó las actividades de las semanas 4 y 5 entre modelado, infraestructura de "
              "experimentos y tablero. Cada integrante registra su trabajo con commits propios en "
              f"{REPO_URL}; los runs de MLflow incluyen la etiqueta «autor».")
    table(doc, cnt, "Responsabilidades individuales", ["Integrante", "Responsabilidades", "Evidencia"], [
        ["Mateo Ríos",
         "Coordinación. Despliegue del servidor MLflow en EC2. Módulo de variables, script de entrenamiento y "
         "experimentos de clasificación y regresión. Selección y registro del modelo campeón. Tablero Dash "
         "(tres pestañas). Integración del reporte.",
         "src/features.py, train.py, run_experiments.sh, select_best.py, report_models.py, deploy/, dashboard/, docs/"],
        ["Harol Perafan",
         "Diseño y ejecución de experimentos adicionales de modelos en MLflow (variantes de hiperparámetros) y "
         "análisis de resultados para las observaciones y conclusiones.",
         "src/run_experiments.sh, runs en MLflow con etiqueta autor"],
        ["Sebastian Vivas",
         "Revisión de la interfaz del tablero frente a la maqueta y mejoras de usabilidad en la pestaña de "
         "predicción; validación funcional del tablero.",
         "dashboard/app.py, dashboard/assets/"],
    ], widths=[2.6, 8.6, 6.0], size=9)
    section_title(doc, None, "Actividades conjuntas y seguimiento")
    bullets(doc, [
        (None, "Definición del protocolo de evaluación (partición, métrica principal y umbral)."),
        (None, "Revisión de los resultados de MLflow y selección del modelo campeón."),
        (None, f"Reunión de cierre el {FECHA}: revisión del tablero, del reporte y de la evidencia en EC2."),
    ])
    out = OUT / "reporte_equipo_e2.docx"
    doc.save(out)
    print("Guardado", out)


if __name__ == "__main__":
    reporte_entrega()
    reporte_equipo()
