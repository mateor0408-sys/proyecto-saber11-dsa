# Imagen del tablero Dash; la URL de la API llega por la variable API_URL
FROM python:3.13-slim

RUN adduser --disabled-password --gecos '' dash-user
WORKDIR /app

COPY docker/requirements-dashboard.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY src/features.py src/features.py
COPY dashboard/ dashboard/
COPY data/processed/saber11_clean.parquet data/processed/saber11_clean.parquet
RUN chown -R dash-user:dash-user /app

USER dash-user
EXPOSE 8050
CMD ["gunicorn", "--chdir", "/app/dashboard", "--workers", "1", "--threads", "4", "--timeout", "120", "--bind", "0.0.0.0:8050", "app:server"]
