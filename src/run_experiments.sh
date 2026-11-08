#!/usr/bin/env bash
# Experimentos de la Entrega 2. Requiere MLFLOW_TRACKING_URI=http://<IP-EC2>:5000
set -euo pipefail
cd "$(dirname "$0")"
T="python train.py"

# --- Clasificación: riesgo de puntaje global < P25 ---
# Línea base y regularización
$T --task clasificacion --model logreg --params C=1 --run-name logreg-base
$T --task clasificacion --model logreg --params C=0.1 class_weight=balanced --run-name logreg-C0.1-bal
$T --task clasificacion --model logreg --params C=1 class_weight=balanced --run-name logreg-C1-bal
# Bosque aleatorio
$T --task clasificacion --model rf --params n_estimators=100 max_depth=14 min_samples_leaf=20 max_samples=0.3 --run-name rf-d14
$T --task clasificacion --model rf --params n_estimators=100 max_depth=20 min_samples_leaf=10 max_samples=0.3 class_weight=balanced --run-name rf-d20-bal
# Gradient boosting
$T --task clasificacion --model hgb --params learning_rate=0.1 max_iter=200 --run-name hgb-lr0.1
$T --task clasificacion --model hgb --params learning_rate=0.05 max_iter=500 max_leaf_nodes=63 --run-name hgb-lr0.05-l63
$T --task clasificacion --model hgb --params learning_rate=0.05 max_iter=500 max_leaf_nodes=63 class_weight=balanced --run-name hgb-lr0.05-l63-bal
# Selección de variables (ablación con el mejor algoritmo)
$T --task clasificacion --model hgb --features hogar --params learning_rate=0.05 max_iter=500 max_leaf_nodes=63 --run-name hgb-solo-hogar
$T --task clasificacion --model hgb --features colegio --params learning_rate=0.05 max_iter=500 max_leaf_nodes=63 --run-name hgb-solo-colegio

# --- Regresión: puntaje global estimado ---
$T --task regresion --model ridge --params alpha=1 --run-name ridge-a1
$T --task regresion --model hgbr --params learning_rate=0.1 max_iter=200 --run-name hgbr-lr0.1
$T --task regresion --model hgbr --params learning_rate=0.05 max_iter=500 max_leaf_nodes=63 --run-name hgbr-lr0.05-l63
