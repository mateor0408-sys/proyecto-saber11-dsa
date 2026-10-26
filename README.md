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
reports/figures/        figuras del EDA
mockup/                 maqueta del tablero
docs/                   reportes de la entrega
```

## Uso
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
dvc pull          # descarga los datos versionados desde S3
# o bien, regenerarlos desde la fuente:
dvc repro
jupyter notebook notebooks/01_eda.ipynb
```
