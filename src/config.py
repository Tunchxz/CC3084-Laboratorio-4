"""Configuracion central: bbox de cada lago y fechas oficiales del laboratorio.

Las fechas son las provistas en el enunciado (Laboratorio 4. Datos Geoespaciales.
2026.pdf) y deben usarse tal cual para que todos los grupos trabajen con la misma
base de imagenes.
"""
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT_DIR / "data" / "raw"
DATA_PROCESSED = ROOT_DIR / "data" / "processed"

LAGOS = {
    "atitlan": {
        "bbox": {
            "west": -91.326256,
            "east": -91.07151,
            "south": 14.5948,
            "north": 14.750979,
        },
        "geojson": DATA_RAW / "lago_atitlan.geojson",
        "fechas": [
            "2025-01-18",
            "2025-04-13",
            "2025-05-13",
            "2025-07-17",
            "2025-11-21",
            "2025-12-29",
            "2026-02-12",
            "2026-03-24",
            "2026-04-13",
            "2026-04-28",
            "2026-07-22",
        ],
    },
    "amatitlan": {
        "bbox": {
            "west": -90.638065,
            "east": -90.512924,
            "south": 14.412347,
            "north": 14.493799,
        },
        "geojson": DATA_RAW / "lago_amatitlan.geojson",
        "fechas": [
            "2025-01-28",
            "2025-04-15",
            "2025-04-28",
            "2025-11-24",
            "2026-01-08",
            "2026-02-02",
            "2026-02-07",  # cobertura valida parcial (~57.1%), ver PDF
            "2026-03-29",
            "2026-04-13",
            "2026-04-28",
            "2026-06-19",
        ],
    },
}

# Bandas Sentinel-2 L2A necesarias para NDVI y NDWI (se descargan via openEO):
# NDVI  -> B04, B08
# NDWI  -> B03, B08
# El indice de cianobacteria NO se descarga banda por banda: se obtiene
# directamente el resultado del script oficial de Sentinel Hub
# "Cyanobacteria Chlorophyll-a NDCI L1C" (CyanoLakes, Kravitz & Matthews 2020)
# via el Process API (ver src/evalscripts/ y src/sentinel_api.py).
BANDAS_REQUERIDAS = ["B03", "B04", "B08"]

OPENEO_BACKEND_URL = "openeo.dataspace.copernicus.eu"
