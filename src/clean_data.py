"""Limpieza de los datos crudos de Saber 11.

Entrada: data/raw/saber11.csv
Salida:  data/processed/saber11_clean.parquet
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

SCORES = [
    "punt_lectura_critica", "punt_matematicas", "punt_c_naturales",
    "punt_sociales_ciudadanas", "punt_ingles", "punt_global",
]

# Umbral de riesgo: percentil 25 nacional del puntaje global
RISK_QUANTILE = 0.25


def clean(src: Path, out: Path) -> None:
    df = pd.read_csv(src, dtype=str)
    n0 = len(df)

    df = df.drop_duplicates(subset="estu_consecutivo")
    for col in SCORES:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # Puntaje global en 0 corresponde a pruebas anuladas
    df = df.dropna(subset=["punt_global"])
    df = df[df["punt_global"] > 0]

    # Edad aproximada al momento de la prueba (año del periodo)
    nac = pd.to_datetime(df["estu_fechanacimiento"], format="%d/%m/%Y", errors="coerce")
    df["edad"] = int(df["periodo"].iloc[0][:4]) - nac.dt.year
    df.loc[~df["edad"].between(13, 60), "edad"] = np.nan
    df = df.drop(columns="estu_fechanacimiento")

    # Normalizaciones de categorías
    df["fami_estratovivienda"] = df["fami_estratovivienda"].replace({"Sin Estrato": "Sin estrato"})
    df["cole_depto_ubicacion"] = df["cole_depto_ubicacion"].str.upper().str.strip()
    for col in df.columns[df.dtypes == object]:
        df[col] = df[col].str.strip().replace({"": np.nan, "-": np.nan})

    threshold = df["punt_global"].quantile(RISK_QUANTILE)
    df["riesgo_bajo_desempeno"] = (df["punt_global"] < threshold).astype(int)

    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print(f"{n0:,} -> {len(df):,} filas | umbral de riesgo P25 = {threshold:.0f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default="data/raw/saber11.csv")
    parser.add_argument("--out", default="data/processed/saber11_clean.parquet")
    args = parser.parse_args()
    clean(Path(args.src), Path(args.out))
