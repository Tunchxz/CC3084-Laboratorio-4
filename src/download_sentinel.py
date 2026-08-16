"""Descarga de los recortes de Sentinel-2 para cada lago y fecha.

Se usa el modulo `openeo` para conectarse al backend de Copernicus Data Space
y descargar unicamente las bandas necesarias sobre el bounding box de cada
lago. Por cada lago y fecha se generan dos GeoTIFF en `data/raw/`:

* `{lago}_{fecha}_L1C.tif` : bandas espectrales (entrada del custom script).
* `{lago}_{fecha}_L2A.tif` : banda SCL (máscara de nubes y sombras).

Ambos comparten proyección, resolución y extensión, por lo que sus pixeles
coinciden uno a uno.

Uso:
    .venv/bin/python src/download_sentinel.py            # todos los lagos
    .venv/bin/python src/download_sentinel.py Amatitlan  # un lago
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import openeo

from config import (
    BANDAS_L1C,
    BANDAS_L2A,
    BBOX,
    COLLECTION_L1C,
    COLLECTION_L2A,
    CRS_SALIDA,
    DATA_RAW,
    FECHAS,
    OPENEO_URL,
    RESOLUCION_M,
)

PRODUCTOS = {
    "L1C": (COLLECTION_L1C, BANDAS_L1C),
    "L2A": (COLLECTION_L2A, BANDAS_L2A),
}


def conectar() -> openeo.Connection:
    """Abre y autentica la conexión con el backend openEO de Copernicus."""
    conexion = openeo.connect(OPENEO_URL)
    conexion.authenticate_oidc()
    return conexion


def ruta_tif(lago: str, fecha: str, producto: str = "L1C") -> Path:
    """Ruta destino del GeoTIFF de un lago, fecha y producto."""
    return DATA_RAW / lago / f"{lago}_{fecha}_{producto}.tif"


def descargar(
    conexion: openeo.Connection, lago: str, fecha: str, producto: str = "L1C"
) -> Path:
    """Descarga el recorte de un lago para una fecha y producto dados."""
    destino = ruta_tif(lago, fecha, producto)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        print(f"  [omitido] ya existe {destino.name}")
        return destino

    coleccion, bandas = PRODUCTOS[producto]

    # openEO usa intervalos temporales semiabiertos [inicio, fin)
    inicio = date.fromisoformat(fecha)
    fin = inicio + timedelta(days=1)

    cubo = conexion.load_collection(
        coleccion,
        spatial_extent=BBOX[lago],
        temporal_extent=[inicio.isoformat(), fin.isoformat()],
        bands=bandas,
    ).resample_spatial(resolution=RESOLUCION_M, projection=CRS_SALIDA)

    cubo.download(destino, format="GTiff")
    tam_mb = destino.stat().st_size / 1e6
    print(f"  [ok] {destino.name} ({tam_mb:.1f} MB)")
    return destino


def main(lagos: list[str]) -> None:
    conexion = conectar()
    for lago in lagos:
        print(f"\n=== {lago} ===")
        for fecha in FECHAS[lago]:
            for producto in PRODUCTOS:
                try:
                    descargar(conexion, lago, fecha, producto)
                except Exception as error:  # noqa: BLE001
                    print(f"  [error] {lago} {fecha} {producto}: {error}")


if __name__ == "__main__":
    seleccion = sys.argv[1:] or list(FECHAS)
    main(seleccion)
