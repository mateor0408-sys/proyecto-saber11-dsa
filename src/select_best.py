"""Selecciona el mejor run de cada experimento, lo registra en el Model Registry de MLflow y lo
exporta a models/ para que el tablero lo cargue directamente.

Criterio: mayor AUC-PR en validación (clasificación) y menor RMSE en validación (regresión).
"""
import json
import shutil
from pathlib import Path

import mlflow

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"
SELECTION = {
    "riesgo": ("saber11-riesgo", "metrics.val_auc_pr DESC"),
    "puntaje": ("saber11-puntaje", "metrics.val_rmse ASC"),
}


def main():
    client = mlflow.MlflowClient()
    summary = {}
    for key, (experiment, order) in SELECTION.items():
        best = mlflow.search_runs(experiment_names=[experiment], order_by=[order], max_results=1,
                                  filter_string="attributes.status = 'FINISHED'").iloc[0]
        uri = f"runs:/{best.run_id}/model"
        version = mlflow.register_model(uri, experiment)
        client.set_registered_model_alias(experiment, "champion", version.version)

        dest = MODELS / key
        shutil.rmtree(dest, ignore_errors=True)
        mlflow.artifacts.download_artifacts(artifact_uri=uri, dst_path=str(MODELS / f"_{key}"))
        (MODELS / f"_{key}" / "model").rename(dest)
        shutil.rmtree(MODELS / f"_{key}")

        summary[key] = {
            "experimento": experiment, "run_id": best.run_id, "run_name": best["tags.mlflow.runName"],
            "version_registro": version.version,
            "metricas": {k.removeprefix("metrics."): round(float(v), 4) for k, v in best.items()
                         if k.startswith("metrics.") and v == v},
        }
        print(f"{key}: {summary[key]['run_name']} -> {experiment} v{version.version}")
    (MODELS / "seleccion.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
