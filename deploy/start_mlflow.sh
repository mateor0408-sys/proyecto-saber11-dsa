#!/usr/bin/env bash
# Arranca el servidor de MLflow ya instalado (por deploy/mlflow_ec2.sh). Usar tras reiniciar la instancia:
#   ssh -i miad-claves-intro.pem ubuntu@<IP> 'bash -s' < deploy/start_mlflow.sh
set -uo pipefail
cd ~/mlflow
pkill -f "[m]lflow server" || true
pkill -f "[h]uey_consumer" || true
# Sin trabajos en segundo plano (huey): consumen ~350 MB que una t3.micro no tiene
MLFLOW_SERVER_ENABLE_JOB_EXECUTION=false nohup .venv/bin/mlflow server \
  --host 0.0.0.0 --port 5000 --workers 1 \
  --backend-store-uri sqlite:///mlflow.db \
  --artifacts-destination ./mlartifacts \
  --allowed-hosts "*" --cors-allowed-origins "*" \
  > mlflow.log 2>&1 &
for _ in $(seq 1 60); do curl -sf -o /dev/null http://localhost:5000/health && break; sleep 2; done
curl -sf -o /dev/null http://localhost:5000/health && echo "MLflow en ejecución (puerto 5000)" || echo "MLflow no respondió"
