"""Genera el reporte final (IEEE) y el reporte de trabajo en equipo de la Entrega final (E3) en .docx.

Parte de la versión del equipo (reporte final y reporte de equipo de S. Vivas y H. Perafan) y la complementa con
la arquitectura, las evidencias de MLflow en EC2, la tabla de endpoints y la ablación de variables. Los manuales
de usuario e instalación son los del equipo (docs/manual_usuario.pdf, docs/manual_instalacion.pdf).
Uso: python docs/build_reportes_e3.py
"""
import json

import pandas as pd
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

from build_reportes import (COL_W, FULL_W, OUT, REPO_URL, ROOT, Counter, base_doc, body, bullets, figure,
                            figure_pair, new_section, references, section_title, set_font, subsection, table,
                            title_block)

FECHA = "24 de noviembre de 2026"
MLFLOW_IP = "54.242.29.105"     # servidor MLflow (EC2 de M. Ríos) durante los experimentos
DEPLOY_IP = "35.153.80.5"       # EC2 de despliegue (S. Vivas), IP pública al momento de las evidencias
DEPLOY_PRIV = "172.31.42.190"
MOD = ROOT / "reports" / "modelos"
TAB = ROOT / "reports" / "tablero"
EV2 = ROOT / "reports" / "evidencias_entrega2"
EV3 = ROOT / "reports" / "evidencias_entrega3"
CAP2 = ROOT / "reports" / "capturas_e2"
ARQ = ROOT / "reports" / "arquitectura" / "arquitectura.png"

CLF = pd.read_csv(MOD / "clasificacion.csv")
REG = pd.read_csv(MOD / "regresion.csv")
SEL = json.loads((ROOT / "models" / "seleccion.json").read_text())
BEST, BEST_REG = SEL["riesgo"], SEL["puntaje"]
M, MR = BEST["metricas"], BEST_REG["metricas"]
BEST_NAME = BEST["run_name"]

REFS = [
    "ICFES, “Resultados únicos Saber 11,” Datos Abiertos Colombia, 2024. [En línea]. Disponible: "
    "https://www.datos.gov.co/Educaci-n/Resultados-nicos-Saber-11/kgxf-xxbe",
    "M. Zaharia et al., “Accelerating the machine learning lifecycle with MLflow,” IEEE Data Eng. Bull., "
    "vol. 41, no. 4, pp. 39–45, 2018.",
    "F. Pedregosa et al., “Scikit-learn: Machine learning in Python,” J. Mach. Learn. Res., vol. 12, "
    "pp. 2825–2830, 2011.",
    "G. Ke et al., “LightGBM: A highly efficient gradient boosting decision tree,” en Proc. NeurIPS, 2017, "
    "pp. 3146–3154.",
    "T. Saito y M. Rehmsmeier, “The precision-recall plot is more informative than the ROC plot when "
    "evaluating binary classifiers on imbalanced datasets,” PLoS ONE, vol. 10, no. 3, e0118432, 2015.",
    "S. Ramírez, “FastAPI.” [En línea]. Disponible: https://fastapi.tiangolo.com",
    "Plotly Technologies Inc., “Dash.” [En línea]. Disponible: https://dash.plotly.com",
    "D. Merkel, “Docker: Lightweight Linux containers for consistent development and deployment,” "
    "Linux J., vol. 2014, no. 239, 2014.",
]


def c(x, d=3):
    """Número con coma decimal."""
    return f"{x:.{d}f}".replace(".", ",")


def run(name):
    return CLF.set_index("run").loc[name]


def note(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    set_font(p.add_run(text), size=8, italic=True)


def abstract(doc, text, keywords):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    set_font(p.add_run("Resumen—"), size=9, bold=True, italic=True)
    set_font(p.add_run(text), size=9, bold=True)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(4), Pt(2)
    set_font(p.add_run("Palabras clave—"), size=9, bold=True, italic=True)
    set_font(p.add_run(keywords), size=9, bold=True)


# ============================================================================= reporte final (IEEE)
def reporte_final():
    doc = base_doc()
    cnt = Counter()
    title_block(doc, "Monitor de Riesgo Académico Saber 11: Modelos, API y Tablero Desplegados en AWS",
                "Proyecto — Entrega final · Despliegue de Soluciones Analíticas · " + FECHA)
    new_section(doc, 2)
    abstract(doc,
             f"Se construyó y desplegó un producto de datos que estima, antes de la prueba, el riesgo de que un "
             f"estudiante obtenga un puntaje global bajo en Saber 11 (< 210, percentil 25 nacional). Tras "
             f"{len(CLF) + len(REG)} experimentos registrados en MLflow sobre AWS EC2, el modelo campeón —un "
             f"gradient boosting basado en histogramas— alcanza AUC-ROC de {c(M['test_auc_roc'])} y recall de "
             f"{c(M['test_recall'], 2)} en prueba, con precisión {c(M['test_precision'] / 0.25, 1)} veces la "
             "tasa base. Los modelos se sirven con una API FastAPI y se consumen desde un tablero Dash de tres "
             "pestañas (diagnóstico territorial, predicción individual explicada y priorización por lotes); ambos "
             "corren en contenedores Docker orquestados con Docker Compose en una instancia EC2.",
             "Saber 11, riesgo académico, gradient boosting, MLflow, FastAPI, Docker, AWS EC2, tablero Dash.")

    # I ---------------------------------------------------------------------------------------------
    section_title(doc, "I", "Resumen del problema")
    body(doc, "El puntaje global de Saber 11 (0–500) condiciona el acceso a la educación superior y a becas, y "
              "muestra brechas territoriales y socioeconómicas marcadas (61 % de estudiantes en el cuartil "
              "inferior en Chocó frente a 12 % en Bogotá). Las secretarías de educación focalizan sus programas "
              "de refuerzo con resultados del año anterior, cuando el estudiante ya presentó la prueba.",
         lead="Contexto.")
    body(doc, "¿Qué estudiantes (y colegios/municipios) tienen mayor riesgo de obtener un puntaje global bajo "
              "(< 210), dadas sus características socioeconómicas y del colegio, para priorizar intervenciones "
              "de refuerzo? El alcance es un prototipo funcional: modelos supervisados empaquetados, una API de "
              "inferencia y un tablero, desplegados con Docker en la nube (AWS).",
         lead="Pregunta de negocio y alcance.")
    body(doc, "Resultados únicos Saber 11 del ICFES (datos.gov.co, kgxf-xxbe) [1], periodo 20224: 532.788 "
              "estudiantes únicos (la fuente publica cada registro dos veces y se deduplica) y 10.378 colegios. "
              "Se usan 19 variables conocidas antes de la prueba. Los datos y modelos se versionan con DVC en S3.",
         lead="Datos.")
    body(doc, "", lead="Cambios respecto a la Entrega 2.")
    bullets(doc, [
        ("API de inferencia:", "los modelos dejaron de cargarse dentro del tablero; ahora los sirve una API "
                               "FastAPI (/health, /features, /modelo, /predict) que acepta lotes de hasta 1.000 "
                               "estudiantes y valores faltantes."),
        ("Tablero desacoplado:", "el tablero pide todas las predicciones a la API mediante la variable API_URL; "
                                 "se verificó que las predicciones coinciden con las del tablero anterior."),
        ("Despliegue:", "API y tablero se empaquetan en dos imágenes Docker y se orquestan con Docker Compose en "
                        "una instancia EC2 (puertos 8000 y 8050)."),
        ("Sin cambios", "en la pregunta de negocio, los datos ni el modelo campeón, que conserva la versión 1 del "
                        "Model Registry."),
    ])

    # II --------------------------------------------------------------------------------------------
    section_title(doc, "II", "Modelos desarrollados y su evaluación")
    subsection(doc, "A", "Variables y selección de características")
    body(doc, "Se usan solo variables disponibles antes de la prueba (src/features.py): nueve del hogar "
              "(educación de madre y padre, estrato, internet, computador, automóvil, lavadora, personas y "
              "cuartos), ocho del colegio (naturaleza, zona, jornada, calendario, bilingüismo, carácter, género "
              "y departamento), el género y la edad. Los puntajes por área se excluyen por fuga de información. "
              "La selección partió del η² del EDA y se validó con una ablación (solo hogar / solo colegio).")
    subsection(doc, "B", "Protocolo de entrenamiento")
    body(doc, "Los nulos categóricos (4–18 %) forman la categoría «Sin información» y la edad se imputa con la "
              "mediana. Partición estratificada 70/15/15 con semilla fija. La selección usa solo validación con "
              "AUC-PR como criterio principal, más informativo que el AUC-ROC con clases desbalanceadas [5]; el "
              "umbral de decisión es el mayor valor con recall ≥ 0,70 en validación "
              f"({c(M['umbral'], 2)}). Se compararon regresión logística, bosque aleatorio y gradient boosting "
              "basado en histogramas de scikit-learn [3], inspirado en LightGBM [4]; para el puntaje global, Ridge "
              "y boosting de regresión.")
    subsection(doc, "C", "Seguimiento en MLflow")
    body(doc, f"Cada ejecución de src/train.py crea un run en un servidor MLflow [2] en EC2 "
              f"(http://{MLFLOW_IP}:5000) con parámetros, métricas de validación y prueba, curvas, matriz de "
              "confusión, importancia por permutación y el modelo con su firma. src/select_best.py registra el "
              "mejor run en el Model Registry (alias «champion») y lo exporta a models/, que es lo que empaqueta "
              "la API. Las Figs. 1–3 evidencian los experimentos con IP y usuario visibles.")
    figure(doc, cnt, CAP2 / "mlflow_experimentos.png",
           f"Runs del experimento saber11-riesgo en MLflow (http://{MLFLOW_IP}:5000); el campeón figura como "
           "modelo registrado saber11-riesgo v1.")
    figure(doc, cnt, CAP2 / "ec2_instancia.png", f"Instancia EC2 del servidor MLflow (IP {MLFLOW_IP}, usuario "
                                                 "visible).")
    figure(doc, cnt, EV2 / "06_random_forest_equipo_70_15_15.png",
           "Run rf-harol-d16-n150 en el servidor MLflow de H. Perafan en EC2 (IP 54.90.207.241).")
    subsection(doc, "D", "Evaluación")
    top = CLF.sort_values("val_auc_pr", ascending=False)
    table(doc, cnt, "Clasificación: métricas en validación", ["Run", "AUC-ROC", "AUC-PR", "Precisión*"],
          [[r.run, c(r.val_auc_roc), c(r.val_auc_pr), c(r.val_precision)] for r in top.itertuples()],
          widths=[3.6, 1.6, 1.6, 1.6])
    note(doc, "* Precisión con el umbral que garantiza recall ≥ 0,70. El bosque rf-harol-d16-n150 (segundo "
              "servidor MLflow) obtuvo AUC-ROC 0,78 y AUC-PR 0,55 en prueba.")
    f_roc = figure(doc, cnt, MOD / "mejor_riesgo_curvas_roc_pr.png",
                   f"Curvas ROC y precisión–recall del campeón ({BEST_NAME}); el punto marca el umbral.")
    table(doc, cnt, "Modelos campeones en el conjunto de prueba", ["Modelo", "Métrica", "Valor"], [
        [BEST_NAME, "AUC-ROC / AUC-PR", f"{c(M['test_auc_roc'])} / {c(M['test_auc_pr'])}"],
        ["", "Recall / Precisión / F1",
         f"{c(M['test_recall'], 2)} / {c(M['test_precision'], 2)} / {c(M['test_f1'], 2)}"],
        [BEST_REG["run_name"], "RMSE / MAE / R²",
         f"{c(MR['test_rmse'], 1)} / {c(MR['test_mae'], 1)} / {c(MR['test_r2'], 2)}"],
    ], widths=[2.9, 3.0, 2.5])
    f_imp = figure(doc, cnt, MOD / "mejor_riesgo_importancia_permutacion.png",
                   "Importancia por permutación (caída del AUC-PR) del modelo campeón.")
    hog, col = run("hgb-solo-hogar"), run("hgb-solo-colegio")
    body(doc, f"El boosting domina con AUC-PR {c(run(BEST_NAME).val_auc_pr)} frente a "
              f"{c(run('rf-d20-bal').val_auc_pr)} del mejor bosque y {c(run('logreg-base').val_auc_pr)} de la "
              "regresión logística, porque captura interacciones como departamento × zona × jornada. Ponderar "
              "clases no cambia el AUC; solo desplaza el umbral. Con solo variables del hogar el AUC-ROC cae a "
              f"{c(hog.val_auc_roc)} y con solo las del colegio a {c(col.val_auc_roc)}: los grupos son "
              f"complementarios. Departamento, edad (extraedad) y jornada dominan la importancia (Fig. {f_imp}). "
              "Las métricas de prueba son prácticamente iguales a las de validación (Fig. "
              f"{f_roc}), sin señales de sobreajuste.")

    # III -------------------------------------------------------------------------------------------
    section_title(doc, "III", "API y despliegue")
    subsection(doc, "A", "Arquitectura")
    body(doc, "La Fig. 6 resume la solución. El ciclo de modelado (DVC, entrenamiento y MLflow) produce la carpeta "
              "models/ con los dos modelos campeones y seleccion.json (run, versión, métricas y umbral). Esa "
              "carpeta se copia en la imagen de la API; la imagen del tablero lleva los datos agregados para el "
              "diagnóstico, pero no los modelos.")
    figure(doc, cnt, ARQ, "Arquitectura: ciclo de modelado (abajo) y despliegue en EC2 con dos contenedores "
                          "Docker comunicados por la red interna de Compose (arriba).")
    subsection(doc, "B", "API de inferencia")
    body(doc, "La API (api/main.py, FastAPI [6]) carga ambos modelos al iniciar y expone cuatro endpoints "
              "(Tabla IV). /predict reutiliza el mismo preprocesamiento del entrenamiento (prepare_X), de modo que "
              "las variables ausentes se tratan igual que en MLflow; una solicitud vacía o sin el campo de "
              "estudiantes se rechaza con el código 422. La documentación interactiva queda en /docs.")
    table(doc, cnt, "Endpoints de la API", ["Endpoint", "Función"], [
        ["GET /health", "Estado del servicio y número de variables (19)."],
        ["GET /features", "Variables que espera el modelo."],
        ["GET /modelo", "Run de MLflow, versión registrada, métricas y umbral."],
        ["POST /predict", "Hasta 1.000 estudiantes; devuelve prob_riesgo, nivel (bajo/medio/alto) y "
                          "puntaje_estimado."],
    ], widths=[2.4, 6.0])
    subsection(doc, "C", "Contenedores y despliegue en AWS")
    body(doc, "Cada componente tiene su Dockerfile [8] (docker/api.Dockerfile y docker/dashboard.Dockerfile) "
              "sobre python:3.13-slim, con usuario sin privilegios y dependencias fijadas a las versiones con las "
              "que se entrenaron los modelos. El tablero corre con gunicorn. docker-compose.yml define los dos "
              "servicios: la API tiene un healthcheck sobre /health y el tablero solo arranca cuando la API está "
              "sana; el tablero la alcanza por la red interna con API_URL=http://api:8000. El despliegue se hizo "
              f"en una instancia EC2 Ubuntu 24.04 (IP pública {DEPLOY_IP}, privada {DEPLOY_PRIV}) con los "
              "puertos 8000 y 8050 abiertos en el grupo de seguridad (Figs. 7–8); en la t3.micro (1 GB) se agregó "
              "memoria de intercambio antes de construir las imágenes. Este enfoque IaaS se eligió por costo y "
              "control dentro de AWS Academy; la misma imagen puede llevarse a ECS.")
    figure(doc, cnt, EV3 / "15_contenedores_compose_ec2.png",
           f"docker compose ps y registros en la EC2 ({DEPLOY_PRIV}): API «healthy», tablero activo y "
           "solicitudes POST /predict desde el tablero.")
    figure(doc, cnt, EV3 / "16_api_desplegada_ec2.png", f"API desplegada: documentación en http://{DEPLOY_IP}:8000/docs.")

    # IV --------------------------------------------------------------------------------------------
    section_title(doc, "IV", "Tablero desarrollado")
    body(doc, "El tablero (dashboard/app.py, Dash [7]) responde la pregunta de negocio en tres pestañas. "
              "(1) Diagnóstico territorial: filtros por departamento, municipio, naturaleza, zona y jornada; "
              "indicadores clave; tasa de riesgo por departamento (un clic baja a municipios); factores con "
              "selector de variable; tabla de municipios o colegios prioritarios y matriz estrato × naturaleza. "
              "(2) Predicción de riesgo: un formulario con el perfil del estudiante devuelve, vía la API, la "
              "probabilidad, el nivel, el puntaje estimado, la tasa de su departamento, una recomendación y los "
              "factores que más pesan (calculados por oclusión frente al perfil más común), con guía de uso, "
              "lectura de niveles y métricas del modelo en servicio. (3) Priorización por lotes: el usuario "
              "descarga una plantilla, carga un CSV y obtiene la lista ordenada por riesgo, descargable. Si la "
              "API no responde, el diagnóstico sigue disponible y las pestañas de predicción muestran un aviso.")
    new_section(doc, 1)
    figure(doc, cnt, EV3 / "14_tablero_desplegado_ec2.png",
           f"Pestaña de predicción del tablero desplegado en EC2 (http://{DEPLOY_IP}:8050).", width=Cm(14))
    figure_pair(doc, cnt, (TAB / "tab1_diagnostico.png", "Pestaña 1 — Diagnóstico territorial."),
                (EV3 / "13_tablero_lotes_via_api.png", "Pestaña 3 — Priorización por lotes servida por la API."))
    new_section(doc, 2)

    # V ---------------------------------------------------------------------------------------------
    section_title(doc, "V", "Principales resultados y conclusiones")
    bullets(doc, [
        ("Respuesta a la pregunta de negocio:", "el producto identifica a 7 de cada 10 estudiantes que "
                                                "terminarán bajo el P25 antes de la prueba. De cada 100 "
                                                f"priorizados ≈ {round(M['test_precision'] * 100)} están realmente "
                                                f"en riesgo, frente a 25 al azar ({c(M['test_precision'] / 0.25, 1)}× "
                                                "más eficiente). Se cumplen los criterios de éxito de la Entrega 1 "
                                                "(AUC ≥ 0,75 y recall ≥ 0,70)."),
        ("Factores:", "el territorio, la extraedad y la jornada explican la mayor parte del riesgo; el hogar y el "
                      "colegio aportan información complementaria, lo que justifica intervenciones combinadas "
                      "(territoriales y de acompañamiento familiar)."),
        ("Límite de las variables:", "las configuraciones de boosting difieren en menos de 0,01 de AUC-PR: el "
                                     "desempeño está limitado por la información disponible, no por el algoritmo. "
                                     f"El puntaje estimado (R² {c(MR['test_r2'], 2)}) es solo orientativo."),
        ("Despliegue:", "separar API y tablero permite actualizar el modelo (nueva versión en MLflow → models/ → "
                        "reconstruir la imagen de la API) sin tocar el tablero, y que otros sistemas consuman las "
                        "predicciones. Compose con healthcheck garantiza el orden de arranque."),
        ("Limitaciones y trabajo futuro:", "un solo periodo (20224); falta validar la estabilidad temporal con "
                                           "otros periodos (p. ej., 20194) y monitorear el modelo en producción. "
                                           "Hay variables sensibles (departamento, "
                                           "género): el modelo prioriza apoyo y no debe usarse para etiquetar "
                                           "estudiantes. Se recomienda HTTPS, autenticación y un dominio antes de "
                                           "un uso real."),
    ])
    body(doc, f"Código, modelos, Dockerfiles y manuales: {REPO_URL}.", lead="Repositorio.")
    references(doc, REFS)
    new_section(doc, 2)
    out = OUT / "reporte_entrega3.docx"
    doc.save(out)
    print("Guardado", out)


# ============================================================================= reporte de equipo
def reporte_equipo():
    """Texto del reporte de equipo de Harol y Sebastian, con los aportes de Mateo en la entrega final."""
    doc = base_doc()
    cnt = Counter()
    title_block(doc, "Reporte de Trabajo en Equipo",
                "Proyecto Monitor de Riesgo Académico Saber 11 — Entrega Final · " + FECHA)
    body(doc, "Repartimos el proyecto en tres frentes: datos y modelos, API y tablero, y despliegue. Cada uno dejó "
              f"su trabajo en commits propios en {REPO_URL}; la API entró a main por un pull request revisado (#2).")
    table(doc, cnt, "Responsabilidades individuales", ["Integrante", "Responsabilidades", "Evidencia"], [
        ["Mateo Ríos",
         "Coordinación y estructura del repositorio. Pipeline DVC, EDA y maqueta. Servidor MLflow en EC2, variables, "
         "entrenamiento, experimentos y selección del modelo campeón. Tablero Dash. En la entrega final: integración "
         "del tablero con la API, ruta /modelo y manejo de valores faltantes en la API; consolidación del reporte "
         "final (arquitectura y evidencias de MLflow), presentación y guion del video.",
         "dvc.yaml, src/, deploy/, dashboard/app.py, api/main.py, README.md, docs/build_reportes_e3.py, docs/video/"],
        ["Harol Perafan",
         "Interpretación del EDA (secciones 3, 4 y 6). Servidor MLflow propio en EC2, experimento de bosque "
         "aleatorio y comparación complementaria de modelos. En la entrega final: implementación de la API de "
         "inferencia con FastAPI y evidencias de la API y del tablero.",
         "PR #1 y #2, api/main.py, src/train_models.py, reports/evidencias_entrega3/01–13"],
        ["Sebastian Vivas",
         "Interpretación del EDA (secciones 1, 2 y 5). Mejoras de usabilidad del tablero (guía de uso, lectura de "
         "niveles, contraste). En la entrega final: contenedores Docker de la API y del tablero, Docker Compose, "
         "despliegue en AWS EC2, evidencias del despliegue, manual de instalación y primera versión del reporte final.",
         "docker/, docker-compose.yml, reports/evidencias_entrega3/14–16, docs/"],
    ], widths=[2.6, 9.4, 5.2], size=9)
    section_title(doc, None, "Actividades conjuntas y seguimiento")
    bullets(doc, [
        (None, "Definimos juntos el protocolo de evaluación y elegimos el modelo campeón."),
        (None, "El 20 de noviembre nos repartimos la entrega final: API, integración del tablero y despliegue."),
        (None, "El 24 de noviembre de 2026 revisamos el despliegue, los documentos finales y el guion del video, en "
               "el que cada uno presenta la parte que desarrolló."),
    ])
    out = OUT / "reporte_equipo_e3.docx"
    doc.save(out)
    print("Guardado", out)


if __name__ == "__main__":
    reporte_final()
    reporte_equipo()
