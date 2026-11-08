#!/usr/bin/env bash
# Instala y arranca el servidor de MLflow en la instancia EC2 (Ubuntu).
# Uso (desde el equipo local):
#   ssh -i miad-claves-intro.pem ubuntu@<IP> 'bash -s' < deploy/mlflow_ec2.sh
# El security group debe permitir TCP 5000 de entrada.
set -euo pipefail
MLFLOW_VERSION="${MLFLOW_VERSION:-3.18.0}"

# Swap de 2 GB: las instancias t3.micro tienen solo 1 GB de RAM
if ! swapon --show | grep -q /swapfile; then
  sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
  sudo mkswap /swapfile > /dev/null && sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab > /dev/null
fi

sudo apt-get update -qq
sudo apt-get install -y -qq python3-venv python3-pip > /dev/null

mkdir -p ~/mlflow && cd ~/mlflow
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q "mlflow==${MLFLOW_VERSION}"

# Arranque del servidor (mismo contenido que deploy/start_mlflow.sh)
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
