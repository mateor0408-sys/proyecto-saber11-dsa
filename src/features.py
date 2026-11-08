"""Definición de variables y preprocesamiento, compartidos por el entrenamiento y el tablero.

Solo se usan variables conocidas antes de presentar la prueba: los puntajes por área se excluyen
porque determinan el puntaje global (fuga de información).
"""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder

MISSING = "Sin información"

HOGAR = [
    "fami_educacionmadre", "fami_educacionpadre", "fami_estratovivienda", "fami_tieneinternet",
    "fami_tienecomputador", "fami_tieneautomovil", "fami_tienelavadora", "fami_personashogar",
    "fami_cuartoshogar",
]
COLEGIO = [
    "cole_naturaleza", "cole_area_ubicacion", "cole_jornada", "cole_calendario", "cole_bilingue",
    "cole_caracter", "cole_genero", "cole_depto_ubicacion",
]
ESTUDIANTE_CAT = ["estu_genero"]
NUMERIC = ["edad"]

FEATURE_SETS = {
    "hogar": HOGAR + ESTUDIANTE_CAT + NUMERIC,
    "colegio": COLEGIO,
    "todas": HOGAR + COLEGIO + ESTUDIANTE_CAT + NUMERIC,
}

TARGET_CLF = "riesgo_bajo_desempeno"
TARGET_REG = "punt_global"


def split_columns(features):
    num = [c for c in features if c in NUMERIC]
    cat = [c for c in features if c not in NUMERIC]
    return cat, num


def prepare_X(df: pd.DataFrame, features) -> pd.DataFrame:
    """Selecciona las variables y marca los nulos categóricos como una categoría propia."""
    cat, num = split_columns(features)
    X = df[features].copy()
    for c in cat:
        X[c] = X[c].astype(object).where(X[c].notna(), MISSING).astype(str)
    for c in num:
        X[c] = pd.to_numeric(X[c], errors="coerce").astype(float)
    return X


def build_preprocessor(features, kind: str) -> ColumnTransformer:
    """`kind='onehot'` para modelos lineales; `kind='ordinal'` para modelos de árboles."""
    cat, num = split_columns(features)
    if kind == "onehot":
        cat_enc = OneHotEncoder(handle_unknown="ignore", min_frequency=50, sparse_output=True)
    else:
        cat_enc = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1,
                                 encoded_missing_value=-1, dtype=np.float64)
    transformers = [("cat", cat_enc, cat)]
    if num:
        transformers.append(("num", make_pipeline(SimpleImputer(strategy="median")), num))
    return ColumnTransformer(transformers, verbose_feature_names_out=False)


def categorical_mask(features):
    """Máscara de columnas categóricas en la salida de `build_preprocessor(..., 'ordinal')`."""
    cat, num = split_columns(features)
    return [True] * len(cat) + [False] * len(num)
