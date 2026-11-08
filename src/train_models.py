"""Entrenamiento reproducible. Ejecutar desde la raiz del proyecto."""
import argparse
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault('OMP_NUM_THREADS', '4')
import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, confusion_matrix, precision_recall_curve,
                             precision_score, recall_score, f1_score, roc_auc_score,
                             mean_absolute_error, root_mean_squared_error, r2_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

FEATURES = ['edad', 'estu_genero', 'fami_estratovivienda', 'fami_educacionmadre',
            'fami_educacionpadre', 'fami_personashogar', 'fami_cuartoshogar',
            'fami_tieneinternet', 'fami_tienecomputador', 'fami_tieneautomovil',
            'fami_tienelavadora', 'cole_naturaleza', 'cole_area_ubicacion',
            'cole_jornada', 'cole_calendario', 'cole_bilingue', 'cole_caracter',
            'cole_genero', 'cole_depto_ubicacion']
SEED = 42

def prep(linear=False):
    cats = FEATURES[1:]
    enc = OneHotEncoder(handle_unknown='ignore') if linear else OrdinalEncoder(
        handle_unknown='use_encoded_value', unknown_value=np.nan, encoded_missing_value=np.nan)
    numeric = Pipeline([('impute', SimpleImputer(strategy='median')), ('scale', StandardScaler())])
    return ColumnTransformer([('age', numeric, ['edad']), ('cats', Pipeline([
        ('impute', SimpleImputer(strategy='constant', fill_value='Sin informacion')),
        ('encode', enc)]), cats)])

def metrics(y, p, threshold):
    pred = p >= threshold
    return dict(auc=roc_auc_score(y, p), average_precision=average_precision_score(y, p),
                precision=precision_score(y, pred, zero_division=0),
                recall=recall_score(y, pred), f1=f1_score(y, pred),
                tn=int(confusion_matrix(y, pred)[0, 0]), fp=int(confusion_matrix(y, pred)[0, 1]),
                fn=int(confusion_matrix(y, pred)[1, 0]), tp=int(confusion_matrix(y, pred)[1, 1]))

def threshold_for(y, p):
    precision, recall, thresholds = precision_recall_curve(y, p)
    valid = np.flatnonzero(recall[:-1] >= .70)
    return float(thresholds[valid[np.argmax(precision[:-1][valid])]])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tracking-uri', default=None)
    args = parser.parse_args()
    out = Path('reports/modeling'); out.mkdir(parents=True, exist_ok=True)
    Path('models').mkdir(exist_ok=True)
    data = Path('data/processed/saber11_clean.parquet')
    df = pd.read_parquet(data)
    assert df.estu_consecutivo.is_unique, 'Estudiantes duplicados'
    X = df[FEATURES].copy()
    X['edad'] = X['edad'].astype(float)
    for c in FEATURES[1:]:
        X[c] = X[c].astype(object).where(X[c].notna(), np.nan)
    y = (df.punt_global < 210).astype(int)
    assert np.array_equal(y, df.riesgo_bajo_desempeno), 'Objetivo previo difiere del umbral 210'
    train, other = train_test_split(np.arange(len(df)), test_size=.4, stratify=y, random_state=SEED)
    val, test = train_test_split(other, test_size=.5, stratify=y.iloc[other], random_state=SEED)
    manifest = dict(seed=SEED, threshold_score=210, sha256=hashlib.sha256(data.read_bytes()).hexdigest(),
                    rows=len(df), features=FEATURES, split={k:len(v) for k,v in [('train',train),('validation',val),('test',test)]})
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    np.savez_compressed(out/'split_indices.npz', train=train, validation=val, test=test)
    uri = args.tracking_uri or os.getenv('MLFLOW_TRACKING_URI') or 'sqlite:///mlflow.db'
    mlflow.set_tracking_uri(uri); mlflow.set_experiment('Saber11_Entrega2_Harol')
    specs = [('dummy', DummyClassifier(strategy='prior'), False),
             ('logistica', LogisticRegression(max_iter=1000, class_weight='balanced', random_state=SEED), True),
             ('boosting_v1', HistGradientBoostingClassifier(categorical_features=[False]+[True]*18, max_iter=120, max_leaf_nodes=15, l2_regularization=1, random_state=SEED), False),
             ('boosting_v2', HistGradientBoostingClassifier(categorical_features=[False]+[True]*18, max_iter=200, max_leaf_nodes=31, l2_regularization=5, random_state=SEED), False)]
    rows, fitted = [], {}
    for name, estimator, linear in specs:
        print('Entrenando', name, flush=True)
        pipe = Pipeline([('prepare', prep(linear)), ('model', estimator)])
        with mlflow.start_run(run_name=name) as run:
            mlflow.log_params({'seed':SEED, 'risk_score_threshold':210, 'data_sha256':manifest['sha256'],
                               **{k:str(v) for k,v in estimator.get_params().items()}})
            pipe.fit(X.iloc[train], y.iloc[train])
            prob = pipe.predict_proba(X.iloc[val])[:, 1]
            threshold = threshold_for(y.iloc[val], prob)
            m = metrics(y.iloc[val], prob, threshold)
            mlflow.log_metrics({'val_'+k:v for k,v in m.items()})
            mlflow.log_param('decision_threshold', threshold)
            mlflow.log_artifact(str(out/'manifest.json'))
            mlflow.sklearn.log_model(pipe, name='model', serialization_format='cloudpickle', input_example=X.iloc[val[:3]])
            rows.append(dict(model=name, run_id=run.info.run_id, threshold=threshold, **m))
            fitted[name] = pipe
    table = pd.DataFrame(rows)
    # Seleccion congelada antes de consultar prueba; precision a recall >= .70.
    candidates = table[(table.model != 'dummy') & (table.auc >= .75) & (table.recall >= .70)]
    if candidates.empty:
        candidates = table[table.model != 'dummy'].sort_values('average_precision', ascending=False)
    else:
        candidates = candidates.sort_values(['precision','average_precision'], ascending=False)
    winner = candidates.iloc[0]
    best = fitted[winner.model]
    final = metrics(y.iloc[test], best.predict_proba(X.iloc[test])[:,1], winner.threshold)
    with mlflow.start_run(run_id=winner.run_id):
        mlflow.log_metrics({'test_'+k:v for k,v in final.items()})
    table.to_csv(out/'classification_validation.csv', index=False)
    result = dict(selected_model=winner.model, run_id=winner.run_id, threshold=float(winner.threshold),
                  test=final, targets_met=bool(final['auc'] >= .75 and final['recall'] >= .70))
    (out/'classification_test.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    joblib.dump(dict(pipeline=best, features=FEATURES, threshold=float(winner.threshold), risk_score_threshold=210), 'models/classifier.joblib')
    print('Evaluacion final:', result, flush=True)
    # Importancia sobre validacion; no se usa para volver a elegir el modelo.
    importance = permutation_importance(best, X.iloc[val[:5000]], y.iloc[val[:5000]],
                                       scoring='roc_auc', n_repeats=3, random_state=SEED)
    pd.DataFrame(dict(feature=FEATURES, auc_decrease=importance.importances_mean,
                      std=importance.importances_std)).sort_values('auc_decrease', ascending=False).to_csv(out/'feature_importance.csv', index=False)
    reg_rows, regs = [], {}
    for name, est in [('reg_dummy', DummyRegressor()), ('reg_boosting', HistGradientBoostingRegressor(
            categorical_features=[False]+[True]*18, max_iter=200, max_leaf_nodes=31, l2_regularization=5, random_state=SEED))]:
        print('Entrenando', name, flush=True)
        p = Pipeline([('prepare', prep()), ('model', est)])
        with mlflow.start_run(run_name=name) as run:
            mlflow.log_params({'seed':SEED, 'data_sha256':manifest['sha256'], **{k:str(v) for k,v in est.get_params().items()}})
            p.fit(X.iloc[train], df.punt_global.iloc[train])
            pred = p.predict(X.iloc[val])
            m = dict(mae=mean_absolute_error(df.punt_global.iloc[val], pred),
                     rmse=root_mean_squared_error(df.punt_global.iloc[val], pred), r2=r2_score(df.punt_global.iloc[val], pred))
            mlflow.log_metrics({'val_'+k:v for k,v in m.items()})
            mlflow.sklearn.log_model(p, name='model', serialization_format='cloudpickle', input_example=X.iloc[val[:3]])
            reg_rows.append(dict(model=name, run_id=run.info.run_id, **m)); regs[name]=p
    rt = pd.DataFrame(reg_rows); rt.to_csv(out/'regression_validation.csv', index=False)
    rw = rt.sort_values('rmse').iloc[0]; rp = regs[rw.model].predict(X.iloc[test])
    rm = dict(mae=mean_absolute_error(df.punt_global.iloc[test],rp), rmse=root_mean_squared_error(df.punt_global.iloc[test],rp), r2=r2_score(df.punt_global.iloc[test],rp))
    with mlflow.start_run(run_id=rw.run_id):
        mlflow.log_metrics({'test_'+k:v for k,v in rm.items()})
        mlflow.log_artifacts(str(out))
    (out/'regression_test.json').write_text(json.dumps(dict(selected_model=rw.model, test=rm), indent=2), encoding='utf-8')
    joblib.dump(dict(pipeline=regs[rw.model], features=FEATURES), 'models/regressor.joblib')
    print('Regresion final:', rm, flush=True)

if __name__ == '__main__':
    main()
