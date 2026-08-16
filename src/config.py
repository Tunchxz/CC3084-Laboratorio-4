"""Configuracion compartida del Laboratorio 4.

Contiene las areas de interes (bounding boxes), las fechas oficiales de cada
lago, las bandas de Sentinel-2 necesarias y las rutas del proyecto.
"""

from pathlib import Path

# --------------------------------------------------------------------------
# Rutas del proyecto
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"

# --------------------------------------------------------------------------
# Conexion al backend openEO
# --------------------------------------------------------------------------
OPENEO_URL = "https://openeo.dataspace.copernicus.eu"

# El custom script de cianobacteria de Sentinel Hub esta escrito para Sentinel-2
# L1C (reflectancia tope de atmosfera): sus umbrales de mascara de agua solo
# funcionan con esos valores. Por eso las bandas espectrales se toman de L1C.
# De L2A se toma unicamente la banda SCL, que clasifica nubes y sombras.
COLLECTION_L1C = "SENTINEL2_L1C"
COLLECTION_L2A = "SENTINEL2_L2A"

# --------------------------------------------------------------------------
# Areas de interes
# --------------------------------------------------------------------------
LAGO_ATITLAN = {
    "west": -91.326256,
    "east": -91.07151,
    "south": 14.5948,
    "north": 14.750979,
}

LAGO_AMATITLAN = {
    "west": -90.638065,
    "east": -90.512924,
    "south": 14.412347,
    "north": 14.493799,
}

BBOX = {
    "Atitlan": LAGO_ATITLAN,
    "Amatitlan": LAGO_AMATITLAN,
}

# Ambos lagos caen dentro de la zona UTM 15 Norte. Fijar la proyeccion y la
# resolucion garantiza que todas las fechas de un mismo lago compartan
# exactamente la misma malla de pixeles.
CRS_SALIDA = "EPSG:32615"
RESOLUCION_M = 20

# --------------------------------------------------------------------------
# Fechas
# --------------------------------------------------------------------------
FECHAS = {
    "Atitlan": [
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
    "Amatitlan": [
        "2025-01-28",
        "2025-04-15",
        "2025-04-28",
        "2025-11-24",
        "2026-01-08",
        "2026-02-02",
        "2026-02-07",
        "2026-03-29",
        "2026-04-13",
        "2026-04-28",
        "2026-06-19",
    ],
}

# Nubosidad (%) de cada escena.
NUBOSIDAD = {
    "Atitlan": {
        "2025-01-18": 0.02,
        "2025-04-13": 0.54,
        "2025-05-13": 4.37,
        "2025-07-17": 3.57,
        "2025-11-21": 3.15,
        "2025-12-29": 3.17,
        "2026-02-12": 0.04,
        "2026-03-24": 3.17,
        "2026-04-13": 0.01,
        "2026-04-28": 4.96,
        "2026-07-22": 4.02,
    },
    "Amatitlan": {
        "2025-01-28": 0.06,
        "2025-04-15": 0.09,
        "2025-04-28": 1.03,
        "2025-11-24": 0.50,
        "2026-01-08": 0.77,
        "2026-02-02": 0.39,
        "2026-02-07": 0.02,
        "2026-03-29": 0.01,
        "2026-04-13": 0.09,
        "2026-04-28": 4.96,
        "2026-06-19": 13.00,
    },
}

# --------------------------------------------------------------------------
# Bandas requeridas
# --------------------------------------------------------------------------
# B03/B04/B08 -> NDVI y NDWI
# B04/B05     -> NDCI (indice de cianobacteria)
# B04/B07/B8A -> FAI (floracion superficial)
# B02/B11/B12 -> máscara de agua del script de Sentinel Hub
BANDAS_L1C = ["B02", "B03", "B04", "B05", "B07", "B08", "B8A", "B11", "B12"]

# SCL -> clasificación de escena (nubes, sombras, agua)
BANDAS_L2A = ["SCL"]

# Factor para pasar de valores digitales de Sentinel-2 L2A a reflectancia 0-1
ESCALA_REFLECTANCIA = 10000.0
