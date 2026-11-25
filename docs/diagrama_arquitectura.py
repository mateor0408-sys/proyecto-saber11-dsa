"""Diagrama de arquitectura del despliegue (Entrega 3) -> reports/arquitectura/arquitectura.png

Uso: python docs/diagrama_arquitectura.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parents[1] / "reports" / "arquitectura" / "arquitectura.png"
BLUE, ORANGE, GREY, INK = "#2a78d6", "#eb6834", "#8a8984", "#1d1d1b"


def box(ax, x, y, w, h, title, lines, color, fill="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                fc=fill, ec=color, lw=1.6))
    ax.text(x + w / 2, y + h - 0.22, title, ha="center", va="top", fontsize=9.5, weight="bold", color=INK)
    ax.text(x + w / 2, y + h - 0.58, "\n".join(lines), ha="center", va="top", fontsize=7.6, color=INK,
            linespacing=1.35)


def arrow(ax, x0, y0, x1, y1, text="", color=INK, dy=0.12, ls="-"):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.3, linestyle=ls, shrinkA=2, shrinkB=2))
    if text:
        ax.text((x0 + x1) / 2, (y0 + y1) / 2 + dy, text, ha="center", va="bottom", fontsize=7.3, color=color)


def main():
    fig, ax = plt.subplots(figsize=(10, 4.6), dpi=200)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.6)
    ax.axis("off")

    # Nube: EC2 de despliegue con Docker Compose
    ax.add_patch(FancyBboxPatch((2.35, 1.75), 5.3, 2.7, boxstyle="round,pad=0.02,rounding_size=0.15",
                                fc="#f3f7fd", ec=BLUE, lw=1.2, ls="--"))
    ax.text(2.5, 4.33, "AWS EC2 · Ubuntu 24.04 · Docker Compose (red interna)", fontsize=8.5, color=BLUE,
            va="top", weight="bold")
    box(ax, 2.6, 2.1, 2.1, 1.75, "Contenedor tablero", ["Dash + gunicorn", "puerto 8050",
                                                          "datos 20224 (parquet)", "API_URL=http://api:8000"], BLUE)
    box(ax, 5.3, 2.1, 2.1, 1.75, "Contenedor API", ["FastAPI + uvicorn", "puerto 8000",
                                                       "/health /modelo /predict", "modelos MLflow (models/)"], BLUE)
    arrow(ax, 4.7, 2.95, 5.3, 2.95, "JSON", BLUE, dy=0.06)

    # Usuario
    box(ax, 0.05, 2.35, 1.45, 1.2, "Usuario", ["secretaría / rector", "navegador web"], GREY)
    arrow(ax, 1.5, 2.95, 2.6, 2.95, "HTTP :8050", INK, dy=0.06)

    # Clientes de la API
    box(ax, 8.4, 2.35, 1.58, 1.2, "Otros sistemas", ["clientes HTTP", "Swagger /docs"], GREY)
    arrow(ax, 8.4, 2.95, 7.4, 2.95, "HTTP :8000", INK, dy=0.06)

    # Ciclo de modelado
    box(ax, 0.1, 0.05, 2.3, 1.35, "Datos (DVC + S3)", ["datos.gov.co → limpieza", "parquet versionado"], ORANGE)
    box(ax, 2.75, 0.05, 2.3, 1.35, "Entrenamiento", ["src/train.py", "13+ experimentos"], ORANGE)
    box(ax, 5.4, 0.05, 2.3, 1.35, "MLflow en EC2", ["Model Registry «champion»", "select_best.py → models/"], ORANGE)
    box(ax, 8.05, 0.05, 1.85, 1.35, "Imágenes Docker", ["models/ + datos", "compose up --build"], ORANGE)
    arrow(ax, 2.4, 0.72, 2.75, 0.72)
    arrow(ax, 5.05, 0.72, 5.4, 0.72)
    arrow(ax, 7.7, 0.72, 8.05, 0.72)
    arrow(ax, 8.97, 1.4, 7.4, 2.4, "", ORANGE, ls="--")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, bbox_inches="tight", facecolor="white")
    print("Guardado", OUT)


if __name__ == "__main__":
    main()
