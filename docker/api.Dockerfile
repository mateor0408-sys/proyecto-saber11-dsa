# Imagen de la API de predicción (FastAPI + modelos exportados de MLflow)
FROM python:3.13-slim

RUN adduser --disabled-password --gecos '' api-user
WORKDIR /app

COPY docker/requirements-api.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY src/features.py src/features.py
COPY api/ api/
COPY models/ models/
RUN chown -R api-user:api-user /app

USER api-user
ENV MLFLOW_DISABLE_AGENT_HINT=1
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
