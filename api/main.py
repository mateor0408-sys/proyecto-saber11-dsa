
"""API de predicción del proyecto Saber 11 – Entrega 3."""

import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import mlflow.sklearn
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from features import FEATURE_SETS, prepare_X  # noqa: E402

MODELS = ROOT / "models"
FEATURES = FEATURE_SETS["todas"]
loaded = {}


class PredictionRequest(BaseModel):
    estudiantes: list[dict] = Field(min_length=1, max_length=1000)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Utilizar únicamente artefactos verificados del equipo.
    loaded["riesgo"] = mlflow.sklearn.load_model(
        str(MODELS / "riesgo")
    )
    loaded["puntaje"] = mlflow.sklearn.load_model(
        str(MODELS / "puntaje")
    )
    seleccion = json.loads(
        (MODELS / "seleccion.json").read_text(encoding="utf-8")
    )
    loaded["umbral"] = float(
        seleccion["riesgo"]["metricas"]["umbral"]
    )
    yield
    loaded.clear()


app = FastAPI(
    title="API Saber 11",
    description="Predicción de riesgo académico y puntaje global",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "modelos": ["riesgo", "puntaje"],
        "variables": len(FEATURES),
    }


@app.get("/features")
def features():
    return {"variables": FEATURES}


@app.post("/predict")
def predict(request: PredictionRequest):
    for i, estudiante in enumerate(request.estudiantes):
        faltantes = [
            c for c in FEATURES if c not in estudiante
        ]
        if faltantes:
            raise HTTPException(
                status_code=422,
                detail={
                    "registro": i,
                    "variables_faltantes": faltantes,
                },
            )

    try:
        frame = pd.DataFrame(request.estudiantes)
        X = prepare_X(frame, FEATURES)

        probabilidades = loaded["riesgo"].predict_proba(X)[:, 1]
        puntajes = loaded["puntaje"].predict(X)
        umbral = loaded["umbral"]

        resultados = []
        for prob, puntaje in zip(probabilidades, puntajes):
            p = float(prob)
            nivel = (
                "alto" if p >= 0.5
                else "medio" if p >= umbral
                else "bajo"
            )
            resultados.append({
                "prob_riesgo": round(p, 4),
                "nivel": nivel,
                "puntaje_estimado": int(round(float(puntaje))),
            })

        return {
            "cantidad": len(resultados),
            "predicciones": resultados,
        }

    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Datos de entrada inválidos: {exc}",
        ) from exc
