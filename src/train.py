"""Entrena un modelo y registra el experimento en MLflow.

Ejemplos:
  python src/train.py --task clasificacion --model logreg --features todas --params C=1 class_weight=balanced
  python src/train.py --task regresion --model hgbr --params learning_rate=0.1 max_iter=300

El servidor de MLflow se toma de la variable de entorno MLFLOW_TRACKING_URI.
"""
import argparse
import subprocess
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd
from mlflow.models import infer_signature
from sklearn.ensemble import (HistGradientBoostingClassifier, HistGradientBoostingRegressor,
                              RandomForestClassifier)
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (ConfusionMatrixDisplay, average_precision_score, f1_score,
                             mean_absolute_error, precision_recall_curve, precision_score,
                             r2_score, recall_score, roc_auc_score, roc_curve,
                             root_mean_squared_error)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from features import (FEATURE_SETS, TARGET_CLF, TARGET_REG, build_preprocessor,
                      categorical_mask, prepare_X)

DATA = Path(__file__).resolve().parents[1] / "data" / "processed" / "saber11_clean.parquet"
SEED = 42
MIN_RECALL = 0.70  # criterio de éxito definido en la Entrega 1
EXPERIMENTS = {"clasificacion": "saber11-riesgo", "regresion": "saber11-puntaje"}
BLUE, ORANGE = "#2a78d6", "#eb6834"
# Tipos internos de scikit-learn que skops no marca como seguros; los modelos los entrenamos nosotros.
SKOPS_TRUSTED = [
    "functools.partial", "numpy.dtype", "sklearn.utils.validation.check_array",
    "sklearn.ensemble._hist_gradient_boosting.predictor.TreePredictor", "sklearn.tree._tree.Tree",
]


def parse_params(items):
    params = {}
    for item in items or []:
        k, v = item.split("=", 1)
        for cast in (int, float):
            try:
                v = cast(v)
                break
            except ValueError:
                pass
        if v == "None":
            v = None
        params[k] = v
    return params


def build_model(task, name, features, params):
    if name == "logreg":
        prep, est = build_preprocessor(features, "onehot"), LogisticRegression(max_iter=2000, **params)
    elif name == "ridge":
        prep, est = build_preprocessor(features, "onehot"), Ridge(**params)
    elif name == "rf":
        prep = build_preprocessor(features, "ordinal")
        est = RandomForestClassifier(n_jobs=-1, random_state=SEED, **params)
    elif name in ("hgb", "hgbr"):
        prep = build_preprocessor(features, "ordinal")
        cls = HistGradientBoostingClassifier if name == "hgb" else HistGradientBoostingRegressor
        est = cls(categorical_features=categorical_mask(features), random_state=SEED, **params)
    else:
        raise ValueError(f"Modelo desconocido: {name}")
    if task == "regresion" and name not in ("ridge", "hgbr"):
        raise ValueError("Para regresión use --model ridge o hgbr")
    return Pipeline([("prep", prep), ("model", est)])


def load_splits(features, target):
    """Partición estratificada 70/15/15 (misma semilla para todos los experimentos)."""
    df = pd.read_parquet(DATA)
    X, y, strat = prepare_X(df, features), df[target], df[TARGET_CLF]
    X_tr, X_tmp, y_tr, y_tmp, s_tr, s_tmp = train_test_split(
        X, y, strat, test_size=0.30, stratify=strat, random_state=SEED)
    X_va, X_te, y_va, y_te = train_test_split(
        X_tmp, y_tmp, test_size=0.50, stratify=s_tmp, random_state=SEED)
    return X_tr, X_va, X_te, y_tr, y_va, y_te


def pick_threshold(y_true, proba):
    """Mayor umbral cuyo recall en validación es ≥ MIN_RECALL (maximiza la precisión)."""
    prec, rec, thr = precision_recall_curve(y_true, proba)
    ok = np.where(rec[:-1] >= MIN_RECALL)[0]
    return float(thr[ok[-1]]) if len(ok) else 0.5


def clf_metrics(y, proba, thr, prefix):
    pred = (proba >= thr).astype(int)
    return {
        f"{prefix}_auc_roc": roc_auc_score(y, proba),
        f"{prefix}_auc_pr": average_precision_score(y, proba),
        f"{prefix}_recall": recall_score(y, pred),
        f"{prefix}_precision": precision_score(y, pred),
        f"{prefix}_f1": f1_score(y, pred),
    }


def reg_metrics(y, pred, prefix):
    return {
        f"{prefix}_rmse": root_mean_squared_error(y, pred),
        f"{prefix}_mae": mean_absolute_error(y, pred),
        f"{prefix}_r2": r2_score(y, pred),
    }


def plot_curves(y, proba, thr, path):
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.8))
    fpr, tpr, _ = roc_curve(y, proba)
    axes[0].plot(fpr, tpr, color=BLUE, lw=2, label=f"AUC = {roc_auc_score(y, proba):.3f}")
    axes[0].plot([0, 1], [0, 1], color="#8a8984", lw=1, ls="--")
    axes[0].set(xlabel="Tasa de falsos positivos", ylabel="Tasa de verdaderos positivos", title="Curva ROC")
    prec, rec, _ = precision_recall_curve(y, proba)
    axes[1].plot(rec, prec, color=BLUE, lw=2, label=f"AP = {average_precision_score(y, proba):.3f}")
    pred = proba >= thr
    axes[1].scatter([recall_score(y, pred)], [precision_score(y, pred)], color=ORANGE, zorder=3,
                    s=50, label=f"umbral = {thr:.2f}")
    axes[1].axhline(y.mean(), color="#8a8984", lw=1, ls="--")
    axes[1].set(xlabel="Recall", ylabel="Precisión", title="Curva precisión–recall")
    for ax in axes:
        ax.legend(loc="lower right" if ax is axes[0] else "upper right", frameon=False)
        ax.grid(color="#e4e3df", lw=0.6)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_confusion(y, pred, path):
    fig, ax = plt.subplots(figsize=(4, 3.6))
    ConfusionMatrixDisplay.from_predictions(y, pred, display_labels=["Sin riesgo", "En riesgo"],
                                            cmap="Blues", values_format=",", ax=ax, colorbar=False)
    ax.set_title("Matriz de confusión (validación)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_importance(pipe, X, y, scoring, path):
    sample = X.sample(min(len(X), 20_000), random_state=SEED)
    res = permutation_importance(pipe, sample, y.loc[sample.index], scoring=scoring, n_repeats=3,
                                 random_state=SEED, n_jobs=-1)
    imp = pd.Series(res.importances_mean, index=X.columns).sort_values()
    fig, ax = plt.subplots(figsize=(6, 0.3 * len(imp) + 1))
    ax.barh(imp.index, imp.values, color=BLUE, height=0.7)
    ax.set(xlabel=f"Caída de {scoring} al permutar la variable", title="Importancia por permutación")
    ax.grid(axis="x", color="#e4e3df", lw=0.6)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return imp


def git_author():
    try:
        return subprocess.check_output(["git", "config", "user.name"], text=True).strip()
    except Exception:
        return "desconocido"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", choices=EXPERIMENTS, required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--features", choices=FEATURE_SETS, default="todas")
    ap.add_argument("--params", nargs="*")
    ap.add_argument("--run-name")
    args = ap.parse_args()

    features = FEATURE_SETS[args.features]
    params = parse_params(args.params)
    target = TARGET_CLF if args.task == "clasificacion" else TARGET_REG
    X_tr, X_va, X_te, y_tr, y_va, y_te = load_splits(features, target)
    pipe = build_model(args.task, args.model, features, params)

    mlflow.set_experiment(EXPERIMENTS[args.task])
    run_name = args.run_name or f"{args.model}-{args.features}"
    with mlflow.start_run(run_name=run_name), tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        mlflow.set_tags({"modelo": args.model, "variables": args.features, "autor": git_author()})
        mlflow.log_params({"modelo": args.model, "variables": args.features,
                           "n_variables": len(features), "n_train": len(X_tr), **params})
        pipe.fit(X_tr, y_tr)

        if args.task == "clasificacion":
            p_va, p_te = pipe.predict_proba(X_va)[:, 1], pipe.predict_proba(X_te)[:, 1]
            thr = pick_threshold(y_va, p_va)
            metrics = {"umbral": thr, **clf_metrics(y_va, p_va, thr, "val"), **clf_metrics(y_te, p_te, thr, "test")}
            plot_curves(y_va, p_va, thr, tmp / "curvas_roc_pr.png")
            plot_confusion(y_va, (p_va >= thr).astype(int), tmp / "matriz_confusion.png")
            scoring = "average_precision"
        else:
            metrics = {**reg_metrics(y_va, pipe.predict(X_va), "val"), **reg_metrics(y_te, pipe.predict(X_te), "test")}
            scoring = "neg_root_mean_squared_error"
        mlflow.log_metrics(metrics)
        imp = plot_importance(pipe, X_va, y_va, scoring, tmp / "importancia_permutacion.png")
        imp.sort_values(ascending=False).to_csv(tmp / "importancia_permutacion.csv", header=["importancia"])
        mlflow.log_artifacts(str(tmp), artifact_path="evaluacion")

        example = X_va.head(5)
        out = pipe.predict_proba(example) if args.task == "clasificacion" else pipe.predict(example)
        mlflow.sklearn.log_model(pipe, name="model", signature=infer_signature(example, out),
                                 input_example=example, skops_trusted_types=SKOPS_TRUSTED)
        shown = {k: round(v, 4) for k, v in metrics.items() if k.startswith("val_") or k == "umbral"}
        print(f"[{run_name}] {shown}")


if __name__ == "__main__":
    main()
