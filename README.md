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
dashboard/app.py        tablero Dash (diagnóstico, predicción, priorización por lotes)
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

### Tablero
```bash
python dashboard/app.py            # http://localhost:8050  (?tab=pred, ?tab=lotes)
```
