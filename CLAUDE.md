# Proyecto Saber 11 — Despliegue de Soluciones Analíticas (MIAD)

Proyecto semestral del curso: producto de datos con **modelos supervisados empaquetados + API de
inferencia + tablero**, desplegado con **Docker**. Se entrega en 3 partes; cada entrega lleva un reporte
IEEE de ≤10 páginas, un reporte de equipo de 1 página y un zip para subir a la plataforma (solo se puede
subir un archivo). Los enunciados están en `../dsa_proy_e1-3.pdf` y `../dsa_proy_e2.pdf`.

**Pregunta de negocio:** ¿qué estudiantes (y colegios/municipios) tienen mayor riesgo de obtener un
puntaje global bajo en Saber 11 (< 210 = P25 nacional), según sus características socioeconómicas y del
colegio, para priorizar intervenciones de refuerzo?

## Equipo
- Mateo Ríos (dueño del repo, coordina; es quien trabaja con Claude).
- Harol Perafan y Sebastian Vivas: **la nota es individual y se mide por commits**, así que cada entrega
  necesita commits propios de ambos. Se les escribe por WhatsApp con mensajes **cortos y naturales** (no
  deben parecer escritos por una IA).
- Harol y Sebastian tienen su propia cuenta de AWS Academy: **no** tienen acceso al bucket S3 ni a la
  instancia EC2 de Mateo (para tener datos usan `dvc repro`).

## Estado
- **Entrega 1 (25-oct-2026):** entregada. Pipeline DVC, EDA, maqueta y reportes.
- **Entrega 2 (8-nov-2026):** lista para subir.
  - 13 experimentos en MLflow sobre EC2.
  - Campeones registrados: `hgb-lr0.05-l63` (riesgo: AUC-ROC 0,800, recall 0,70, precisión 0,48 en prueba)
    y `hgbr-lr0.05-l63` (puntaje: RMSE 40,7).
  - Tablero Dash con 3 pestañas.
  - Reporte en `docs/reporte_entrega2.pdf` (7 páginas) y zip en `../Entrega2_Saber11.zip`.

### Pendiente inmediato
1. **Harol ya hizo su commit** (c4f9428): un pipeline de modelado propio en su EC2, con
   `src/train_models.py`, `src/summarize_models.py`, `src/verify_models.py` y `requirements-modeling*.txt`.
   Sus resultados están en `reports/modeling/` y las evidencias de MLflow en
   `reports/**/evidencias_entrega2/`. **Ajustar su fila** del reporte de equipo en
   `docs/build_reportes_e2.py` (hoy dice "experimento en run_experiments.sh") para describir este trabajo
   real. Si aporta, citar sus evidencias en el reporte principal.
2. Falta el commit de Sebastian (mejora de `dashboard/app.py` o `dashboard/assets/style.css`).
   Verificarlo con `git pull` + `git log`.
3. Regenerar los PDFs (`docs/build_reportes_e2.py` + docx2pdf) y el zip `../Entrega2_Saber11.zip`, con el
   mismo esquema que el actual: LEEME + 2 PDF + `git archive` del repo + `reports/capturas_e2/`.
   Mateo sube el zip.

### Siguiente: Entrega 3 (pendiente de enunciado)
API FastAPI que sirva los modelos de `models/` + tablero consumiendo la API (hoy carga el modelo
directamente) + Docker en EC2. Puertos 8000 (API) y 8050 (tablero) ya están abiertos en el security group.
Pendiente también: validar estabilidad temporal con el periodo 20194.

## Estructura y comandos
```
src/download_data.py, src/clean_data.py   pipeline DVC (dvc.yaml): datos -> data/processed/saber11_clean.parquet
src/features.py        19 variables previas a la prueba + preprocesamiento (compartido con el tablero)
src/train.py           entrena 1 modelo y lo registra en MLflow (MLFLOW_TRACKING_URI)
src/run_experiments.sh experimentos de la Entrega 2
src/select_best.py     mejor run -> Model Registry (alias champion) -> models/ (DVC) + models/seleccion.json
src/report_models.py   tablas/figuras de modelos desde MLflow -> reports/modelos/
dashboard/app.py       tablero Dash (?tab=diag|pred|lotes, &demo=1 para lotes de ejemplo)
deploy/mlflow_ec2.sh   instala MLflow en EC2 (solo la primera vez)
deploy/start_mlflow.sh arranca MLflow (usar tras reiniciar la instancia)
docs/build_reportes.py      reportes E1 + helpers IEEE reutilizables
docs/build_reportes_e2.py   reportes E2 (lee cifras de reports/modelos/*.csv y models/seleccion.json)
```
- Entorno: `.venv/` (Python 3.13 de Anaconda). Usar `.venv/bin/python`, `.venv/bin/dvc`.
- Tablero: `.venv/bin/python dashboard/app.py` → http://localhost:8050.
- Capturas del tablero: Chrome headless (`--virtual-time-budget=25000`) sobre `?tab=...`.
- PDFs: `.venv/bin/docx2pdf` (usa Microsoft Word; cerrar documentos abiertos antes).
- Verificar páginas: con `pymupdf`.

## Infraestructura y gotchas
- **GitHub:** https://github.com/mateor0408-sys/proyecto-saber11-dsa (público). El push funciona con la
  credencial guardada en el llavero.
- **DVC remoto:** `s3://mateorios2002-dvcstore/saber11` (us-east-1). Versiona `data/` y `models/`.
- **AWS Academy Learner Lab:** las credenciales vencen en cada sesión. Mateo pega las nuevas en
  `~/.aws/credentials` (AWS Details → Show). Con `RequestExpired`/`ExpiredToken`, pedírselas.
  - *End Lab* no borra nada; **Reset** sí lo borra todo (no usarlo).
- **EC2:** `mlflow-saber11` (i-0e672352e5f6c832a), Ubuntu 24.04, **t3.micro (1 GB RAM)**, llave
  `../miad-claves-intro.pem`, usuario `ubuntu`.
  - La IP pública cambia al detener/encender (en la E2 fue 54.242.29.105).
  - MLflow en el puerto 5000, con backend SQLite y artefactos en `~/mlflow/`.
  - El enunciado exige dejarla **detenida, no terminada**.
- **Errores a evitar en la t3.micro:**
  - Arrancar MLflow con `MLFLOW_SERVER_ENABLE_JOB_EXECUTION=false` y `--workers 1`; los procesos `huey`
    saturan la RAM. `start_mlflow.sh` ya lo hace.
  - Nunca reinstalar (apt/pip) con el servidor corriendo: la máquina deja de responder incluso por SSH.
  - El entrenamiento corre en el Mac; EC2 solo registra.
  - En `pkill -f` remoto usar patrones como `"[m]lflow server"` para no matar la propia sesión SSH.
- **MLflow 3.18** guarda modelos con skops: los tipos de sklearn se declaran en `SKOPS_TRUSTED` de
  `src/train.py`.
- **Datos:** la fuente publica cada registro dos veces (se deduplica por `estu_consecutivo`). Hay 532.788
  estudiantes únicos del periodo 20224.

## Convenciones
- Todo en español. Reportes en **formato IEEE**: dos columnas, Times New Roman 10 pt, se generan por script
  y regenerar sobrescribe los .docx.
- Commits con mensajes en español, incrementales.
- Al cerrar una entrega: dejar PDFs en `docs/` y el zip en `../`; recordar detener la EC2.
