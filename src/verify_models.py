"""Verifica particiones, artefactos cargables y coincidencia con metricas MLflow."""
import json
from pathlib import Path
import joblib
import mlflow
import numpy as np
import pandas as pd

out = Path('reports/modeling')
split = np.load(out/'split_indices.npz')
a,b,c = (set(split[k]) for k in ['train','validation','test'])
assert not (a & b or a & c or b & c), 'Particiones solapadas'
df = pd.read_parquet('data/processed/saber11_clean.parquet')
assert len(a|b|c) == len(df)
bundle = joblib.load('models/classifier.joblib')
reg = joblib.load('models/regressor.joblib')
X = df[bundle['features']].head(10).copy()
X['edad'] = X['edad'].astype(float)
for col in bundle['features'][1:]:
    X[col] = X[col].astype(object).where(X[col].notna(), np.nan)
# Perfil incompleto y categoria no vista deben producir predicciones validas.
X.loc[X.index[0], 'edad'] = np.nan
X.loc[X.index[0], 'cole_depto_ubicacion'] = 'CATEGORIA_NO_VISTA'
X.loc[X.index[1], 'fami_educacionmadre'] = np.nan
p = bundle['pipeline'].predict_proba(X)[:,1]
score = reg['pipeline'].predict(X)
assert np.isfinite(p).all() and ((p>=0)&(p<=1)).all()
assert np.isfinite(score).all()
mlflow.set_tracking_uri('sqlite:///mlflow.db')
result = json.loads((out/'classification_test.json').read_text())
run = mlflow.get_run(result['run_id'])
assert run.info.status == 'FINISHED'
for key,value in result['test'].items():
    assert np.isclose(run.data.metrics['test_'+key], value)
runs = mlflow.search_runs(experiment_names=['Saber11_Entrega2_Harol'])
assert len(runs[runs['status']=='FINISHED']) >= 6
print('VERIFICADO: particiones sin solapamiento; pipelines cargables; entradas faltantes y nuevas; metricas coinciden con MLflow; seis experimentos finalizados.')
