"""Descarga los resultados de Saber 11 desde datos.gov.co (API Socrata).

Fuente: "Resultados únicos Saber 11" (id kgxf-xxbe).
Salida: data/raw/saber11.csv
"""
import argparse
import io
import time
from pathlib import Path

import pandas as pd
import requests

URL = "https://www.datos.gov.co/resource/kgxf-xxbe.csv"
PAGE_SIZE = 50_000
RETRIES = 5

COLUMNS = [
    "periodo", "estu_consecutivo", "estu_genero", "estu_fechanacimiento",
    "estu_depto_reside", "estu_mcpio_reside",
    "fami_estratovivienda", "fami_educacionmadre", "fami_educacionpadre",
    "fami_personashogar", "fami_cuartoshogar", "fami_tieneinternet",
    "fami_tienecomputador", "fami_tieneautomovil", "fami_tienelavadora",
    "cole_naturaleza", "cole_area_ubicacion", "cole_jornada", "cole_calendario",
    "cole_bilingue", "cole_caracter", "cole_genero",
    "cole_cod_dane_establecimiento", "cole_nombre_establecimiento",
    "cole_depto_ubicacion", "cole_cod_depto_ubicacion",
    "cole_mcpio_ubicacion", "cole_cod_mcpio_ubicacion",
    "punt_lectura_critica", "punt_matematicas", "punt_c_naturales",
    "punt_sociales_ciudadanas", "punt_ingles", "punt_global", "desemp_ingles",
]


def download(periodo: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    pages, offset = [], 0
    while True:
        params = {
            "$select": ",".join(COLUMNS),
            "$where": f"periodo='{periodo}'",
            "$order": ":id",
            "$limit": PAGE_SIZE,
            "$offset": offset,
        }
        for attempt in range(RETRIES):
            try:
                resp = requests.get(URL, params=params, timeout=300)
                resp.raise_for_status()
                break
            except requests.RequestException as err:
                print(f"  reintento {attempt + 1}/{RETRIES}: {err}")
                time.sleep(10)
        else:
            raise RuntimeError(f"No fue posible descargar el offset {offset}")
        page = pd.read_csv(io.StringIO(resp.text), dtype=str)
        if page.empty:
            break
        pages.append(page)
        offset += len(page)
        print(f"  {offset:,} registros descargados")
        if len(page) < PAGE_SIZE:
            break
    df = pd.concat(pages, ignore_index=True)
    df.to_csv(out, index=False)
    print(f"Guardado {out} ({len(df):,} filas, {df.shape[1]} columnas)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--periodo", default="20224")
    parser.add_argument("--out", default="data/raw/saber11.csv")
    args = parser.parse_args()
    download(args.periodo, Path(args.out))
