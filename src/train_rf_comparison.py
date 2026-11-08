"""RF adicional en la particion original; comparar solo con validacion."""
import hashlib
import json
from pathlib import Path
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from train_models import FEATURES, SEED, prep, metrics, threshold_for

root = Path(__file__).resolve().parents[1]
out = root/'reports/modeling'
data = root/'data/processed/saber11_clean.parquet'
manifest = json.loads((out/'manifest.json').read_text())
assert hashlib.sha256(data.read_bytes()).hexdigest() == manifest['sha256']
df = pd.read_parquet(data)
y = (df.punt_global < 210).astype(int)
split_path = out/'split_indices.npz'
if not split_path.exists():
    # Reproduce exactamente la particion de train_models.py con los mismos datos.
    train_idx, other = train_test_split(np.arange(len(df)), test_size=.4,
                                       stratify=y, random_state=SEED)
    val_idx, test_idx = train_test_split(other, test_size=.5,
                                       stratify=y.iloc[other], random_state=SEED)
    np.savez_compressed(split_path, train=train_idx, validation=val_idx, test=test_idx)
split = np.load(split_path)
train, val = split['train'], split['validation']
X = df[FEATURES].copy()
X['edad'] = X['edad'].astype(float)
for c in FEATURES[1:]:
    X[c] = X[c].astype(object).where(X[c].notna(), np.nan)
params = dict(n_estimators=150, max_depth=16, min_samples_leaf=15,
              max_samples=.35, class_weight='balanced', random_state=SEED, n_jobs=4)
pipe = Pipeline([('prepare', prep()), ('model', RandomForestClassifier(**params))])
mlflow.set_tracking_uri('http://98.84.169.156:5000')
mlflow.set_experiment('Saber11_Entrega2_Harol')
with mlflow.start_run(run_name='Random Forest') as run:
    mlflow.set_tags({'autor':'Harol Perafan', 'comparison':'validation_only_60_20_20'})
    mlflow.log_params({**params, 'data_sha256':manifest['sha256'], 'risk_score_threshold':210,
                       'n_train':len(train), 'n_validation':len(val)})
    print('Entrenando RF en la particion original', flush=True)
    pipe.fit(X.iloc[train], y.iloc[train])
    prob = pipe.predict_proba(X.iloc[val])[:,1]
    threshold = threshold_for(y.iloc[val], prob)
    m = metrics(y.iloc[val], prob, threshold)
    mlflow.log_param('decision_threshold', threshold)
    mlflow.log_metrics({'val_'+k:v for k,v in m.items()})
    mlflow.log_artifact(str(out/'manifest.json'))
    mlflow.sklearn.log_model(pipe, name='model', serialization_format='cloudpickle',
                             pip_requirements=str(root/'requirements-modeling.txt'),
                             input_example=X.iloc[val[:5]])
    result = dict(model='Random Forest', run_id=run.info.run_id,
                  threshold=threshold, **m)
    (out/'random_forest_comparison.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    original = pd.read_csv(out/'classification_validation.csv')
    original = original[original.model != result['model']]
    pd.concat([original, pd.DataFrame([result])], ignore_index=True).to_csv(
        out/'classification_validation_with_rf.csv', index=False)
    print(json.dumps(result, indent=2), flush=True)
    print('Se conserva el modelo seleccionado originalmente. No se consulto prueba.', flush=True)

