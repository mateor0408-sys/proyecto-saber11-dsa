"""Consulta los experimentos en MLflow y genera las tablas y figuras de modelos para el reporte.

Salidas en reports/modelos/:
  clasificacion.csv, regresion.csv          métricas de todos los runs
  comparacion_clasificacion.png             AUC-ROC y AUC-PR de validación por run
  mejor_*.png                               artefactos de evaluación del modelo seleccionado
"""
import json
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "modelos"
BLUE, ORANGE, MUTED = "#2a78d6", "#eb6834", "#52514e"


def runs(experiment, metrics):
    df = mlflow.search_runs(experiment_names=[experiment], filter_string="attributes.status = 'FINISHED'")
    cols = {"tags.mlflow.runName": "run", "tags.modelo": "modelo", "tags.variables": "variables",
            "tags.autor": "autor", "run_id": "run_id", **{f"metrics.{m}": m for m in metrics}}
    return df[list(cols)].rename(columns=cols)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    clf = runs("saber11-riesgo", ["val_auc_roc", "val_auc_pr", "val_recall", "val_precision", "val_f1", "umbral",
                                  "test_auc_roc", "test_auc_pr", "test_recall", "test_precision", "test_f1"])
    clf = clf.sort_values("val_auc_pr", ascending=False).drop_duplicates("run")
    reg = runs("saber11-puntaje", ["val_rmse", "val_mae", "val_r2", "test_rmse", "test_mae", "test_r2"])
    reg = reg.sort_values("val_rmse").drop_duplicates("run")
    clf.round(4).to_csv(OUT / "clasificacion.csv", index=False)
    reg.round(4).to_csv(OUT / "regresion.csv", index=False)

    plot = clf.sort_values("val_auc_pr")
    fig, ax = plt.subplots(figsize=(7, 0.32 * len(plot) + 1.2))
    y = range(len(plot))
    ax.barh([i + 0.2 for i in y], plot.val_auc_roc, height=0.38, color=BLUE, label="AUC-ROC")
    ax.barh([i - 0.2 for i in y], plot.val_auc_pr, height=0.38, color=ORANGE, label="AUC-PR")
    ax.set_yticks(list(y), plot.run)
    for i, (r, p) in enumerate(zip(plot.val_auc_roc, plot.val_auc_pr)):
        ax.text(r + 0.005, i + 0.2, f"{r:.3f}", va="center", fontsize=7, color=MUTED)
        ax.text(p + 0.005, i - 0.2, f"{p:.3f}", va="center", fontsize=7, color=MUTED)
    ax.set_xlim(0.3, 0.9)
    ax.set_xlabel("Métrica en validación")
    ax.set_title("Comparación de modelos de clasificación (MLflow)", fontweight="bold")
    ax.legend(loc="lower right", frameon=False)
    ax.grid(axis="x", color="#e4e3df", lw=0.6)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "comparacion_clasificacion.png", dpi=200)
    plt.close(fig)

    selection = json.loads((ROOT / "models" / "seleccion.json").read_text())
    for key in ("riesgo", "puntaje"):
        tmp = mlflow.artifacts.download_artifacts(run_id=selection[key]["run_id"], artifact_path="evaluacion",
                                                  dst_path=str(OUT / f"_{key}"))
        for f in Path(tmp).glob("*.png"):
            shutil.copy(f, OUT / f"mejor_{key}_{f.name}")
        shutil.rmtree(OUT / f"_{key}")
    print(clf[["run", "val_auc_roc", "val_auc_pr", "val_recall", "val_precision", "autor"]].to_string(index=False))
    print(reg[["run", "val_rmse", "val_mae", "val_r2"]].to_string(index=False))


if __name__ == "__main__":
    main()
