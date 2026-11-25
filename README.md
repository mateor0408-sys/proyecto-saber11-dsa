# Monitor de riesgo académico — Saber 11

Proyecto del curso *Despliegue de soluciones analíticas* (MIAD).

**Pregunta de negocio:** ¿Qué estudiantes (y colegios/municipios) tienen mayor riesgo de obtener un puntaje
global bajo en Saber 11, dadas sus características socioeconómicas y del colegio, para priorizar
intervenciones de refuerzo?

**Producto:** modelo supervisado (riesgo de puntaje global < P25 y puntaje estimado), API de inferencia y
tablero, desplegados con Docker.

## Equipo
- Mateo Ríos
- Harol Perafan
- Sebastian Vivas

## Datos
[Resultados únicos Saber 11](https://www.datos.gov.co/Educaci-n/Resultados-nicos-Saber-11/kgxf-xxbe)
(datos.gov.co, ICFES), periodo `20224`. Los datos no se guardan en Git: se versionan con DVC en un remoto S3.

## Estructura
```
src/download_data.py    descarga desde la API Socrata -> data/raw/saber11.csv
src/clean_data.py       limpieza y variable objetivo  -> data/processed/saber11_clean.parquet
dvc.yaml                pipeline (download -> clean)
notebooks/01_eda.ipynb  exploración de datos
src/features.py         variables del modelo y preprocesamiento
src/train.py            entrenamiento + registro en MLflow (un run por ejecución)
src/run_experiments.sh  experimentos de la Entrega 2
src/select_best.py      mejor run -> Model Registry de MLflow y models/ (DVC)
src/report_models.py    tablas y figuras de modelos para el reporte
api/main.py             API FastAPI que sirve los modelos de models/ (/health, /modelo, /predict)
dashboard/app.py        tablero Dash (diagnóstico, predicción, priorización por lotes); predice vía la API
deploy/mlflow_ec2.sh    instala y arranca el servidor MLflow en EC2
reports/                figuras del EDA y de los modelos
mockup/                 maqueta del tablero
docs/                   reportes de las entregas
```

## Uso
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
dvc pull          # datos y modelos versionados desde S3
# o bien, regenerar los datos desde la fuente:
dvc repro
```

### Experimentos con MLflow (servidor en EC2)
```bash
ssh -i miad-claves-intro.pem ubuntu@<IP-EC2> 'bash -s' < deploy/mlflow_ec2.sh   # una sola vez
export MLFLOW_TRACKING_URI=http://<IP-EC2>:5000
python src/train.py --task clasificacion --model hgb --params learning_rate=0.05 max_iter=500
bash src/run_experiments.sh        # todos los experimentos
python src/select_best.py          # registra y exporta el mejor modelo a models/
```

### API y tablero
El tablero no carga los modelos: todas las predicciones las pide a la API. Primero se levanta la API
(necesita `models/`) y luego el tablero (necesita `data/processed/`), indicándole la URL de la API.
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000      # documentación en http://localhost:8000/docs
API_URL=http://localhost:8000 python dashboard/app.py # http://localhost:8050  (?tab=pred, ?tab=lotes)
```
- `GET /health`: estado de la API. `GET /modelo`: run de MLflow, versión, métricas y umbral en servicio.
- `POST /predict` con `{"estudiantes": [{...}, ...]}` (máx. 1000 por solicitud; las variables ausentes o
  nulas se tratan como "Sin información"). Devuelve `prob_riesgo`, `nivel` y `puntaje_estimado`.
- `API_URL` vale `http://localhost:8000` por defecto; en contenedores se apunta al servicio de la API.
- Si la API no responde, el tablero sigue funcionando (diagnóstico territorial) y muestra el aviso en
  las pestañas de predicción.

### Despliegue con Docker
La API y el tablero corren en dos contenedores definidos en `docker-compose.yml` (`docker/api.Dockerfile` y
`docker/dashboard.Dockerfile`). El tablero llega a la API por la red interna de Compose con
`API_URL=http://api:8000`. Antes de construir deben existir `models/` y `data/processed/saber11_clean.parquet`
(`dvc pull` o `dvc repro`), porque se copian dentro de las imágenes.
```bash
docker compose up -d --build     # API en http://<IP>:8000/docs, tablero en http://<IP>:8050
docker compose ps                # estado de los dos servicios
docker compose logs -f           # registros de ambos contenedores
docker compose down              # detener
```
En EC2 deben estar abiertos los puertos 8000 y 8050 en el grupo de seguridad.

## Documentos de la entrega final
- `docs/reporte_entrega3.pdf`: reporte final (IEEE), generado con `docs/build_reportes_e3.py`; el diagrama de
  arquitectura sale de `docs/diagrama_arquitectura.py`.
- `docs/manual_usuario.pdf` y `docs/manual_instalacion.pdf`: manuales del tablero.
- `docs/reporte_equipo_e3.pdf`: reporte de trabajo en equipo.
- `docs/video/`: diapositivas de apoyo y guion del video (`guion.json` alimenta las notas del orador y el guion;
  `build_deck.js` genera la presentación y `build_guion.py` el guion).
