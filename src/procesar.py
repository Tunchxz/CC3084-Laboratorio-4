"""Genera las capas de índices y la tabla de estadisticas por lago y fecha.

Lee los GeoTIFF crudos de `data/raw/`, calcula NDVI, NDWI, NDCI, FAI y
clorofila-a con `indices.py`, y escribe en `data/processed/`:

* `{lago}/{lago}_{fecha}_indices.tif` : GeoTIFF de 7 bandas con los índices.
* `{lago}/{lago}_mascara_lago.tif`    : máscara fija del espejo de agua.
* `estadisticas_por_fecha.csv`        : resumen por lago y fecha.

La máscara fija del lago se define como los pixeles clasificados como agua en
al menos el 60% de las fechas. Sirve para que todas las fechas se comparen
sobre exactamente la misma superficie.

Uso:
    .venv/bin/python src/procesar.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import rasterio

from config import DATA_PROCESSED, DATA_RAW, FECHAS, NUBOSIDAD, RESOLUCION_M
from indices import calcular_indices

# Bandas que se guardan en el GeoTIFF de índices, en orden.
CAPAS = ["ndvi", "ndwi", "ndci", "fai", "chla", "agua", "validos"]

# Umbral de clorofila-a (mg/m3) a partir del cual se considera un valor alto.
# La OMS asocia concentraciones sobre ~20 mg/m3 con riesgo moderado por
# cianobacterias en aguas recreativas.
UMBRAL_CHLA_ALTO = 20.0

# Umbral de FAI del custom script para floracion flotante en superficie.
UMBRAL_FAI = 0.08

# Fracción de fechas en las que un pixel debe ser agua para formar parte de la
# máscara fija del lago.
FRACCION_AGUA_LAGO = 0.6

AREA_PIXEL_KM2 = (RESOLUCION_M**2) / 1e6


def ruta_indices(lago: str, fecha: str):
    return DATA_PROCESSED / lago / f"{lago}_{fecha}_indices.tif"


def ruta_mascara(lago: str):
    return DATA_PROCESSED / lago / f"{lago}_mascara_lago.tif"


def ruta_cruda(lago: str, fecha: str, producto: str = "L1C"):
    return DATA_RAW / lago / f"{lago}_{fecha}_{producto}.tif"


def _perfil(lago: str, fecha: str, n_bandas: int) -> dict:
    with rasterio.open(ruta_cruda(lago, fecha)) as origen:
        perfil = origen.profile.copy()
    perfil.update(
        count=n_bandas, dtype="float32", nodata=np.nan, compress="deflate"
    )
    return perfil


def guardar_indices(lago: str, fecha: str, capas: dict[str, np.ndarray]) -> None:
    """Escribe las capas derivadas como un GeoTIFF multibanda."""
    destino = ruta_indices(lago, fecha)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(destino, "w", **_perfil(lago, fecha, len(CAPAS))) as salida:
        for i, nombre in enumerate(CAPAS, start=1):
            salida.write(capas[nombre].astype("float32"), i)
            salida.set_band_description(i, nombre)


def leer_indices(lago: str, fecha: str) -> dict[str, np.ndarray]:
    """Lee el GeoTIFF de índices ya generado."""
    with rasterio.open(ruta_indices(lago, fecha)) as src:
        datos = src.read()
        nombres = list(src.descriptions)
    capas = {nombre: datos[i] for i, nombre in enumerate(nombres)}
    for mascara in ("agua", "validos"):
        capas[mascara] = capas[mascara] > 0.5
    return capas


def leer_mascara_lago(lago: str) -> np.ndarray:
    """Lee la máscara fija del espejo de agua del lago."""
    with rasterio.open(ruta_mascara(lago)) as src:
        return src.read(1) > 0.5


def construir_mascara_lago(lago: str) -> np.ndarray:
    """Pixeles clasificados como agua en al menos el 60% de las fechas."""
    fechas = FECHAS[lago]
    acumulado = None
    for fecha in fechas:
        agua = leer_indices(lago, fecha)["agua"].astype(np.float32)
        acumulado = agua if acumulado is None else acumulado + agua
    mascara = (acumulado / len(fechas)) >= FRACCION_AGUA_LAGO

    destino = ruta_mascara(lago)
    with rasterio.open(destino, "w", **_perfil(lago, fechas[0], 1)) as salida:
        salida.write(mascara.astype("float32"), 1)
        salida.set_band_description(1, "mascara_lago")
    return mascara


def resumen(
    lago: str, fecha: str, capas: dict[str, np.ndarray], lago_mask: np.ndarray
) -> dict:
    """Estadísticas de una escena restringidas al espejo de agua del lago."""
    usable = lago_mask & capas["validos"]
    chla = capas["chla"][usable]
    chla = chla[np.isfinite(chla)]
    fai = capas["fai"][usable]
    fai = fai[np.isfinite(fai)]

    def promedio(nombre: str) -> float:
        valores = capas[nombre][usable]
        return float(np.nanmean(valores)) if np.isfinite(valores).any() else np.nan

    return {
        "lago": lago,
        "fecha": pd.Timestamp(fecha),
        "nubosidad_pct": NUBOSIDAD[lago][fecha],
        "area_lago_km2": float(lago_mask.sum() * AREA_PIXEL_KM2),
        "cobertura_valida_pct": float(usable.sum() / lago_mask.sum() * 100),
        "pixeles_analizados": int(chla.size),
        "ndci_medio": promedio("ndci"),
        "chla_media": promedio("chla"),
        "chla_mediana": float(np.median(chla)) if chla.size else np.nan,
        "chla_p90": float(np.percentile(chla, 90)) if chla.size else np.nan,
        "chla_max": float(chla.max()) if chla.size else np.nan,
        "ndvi_medio": promedio("ndvi"),
        "ndwi_medio": promedio("ndwi"),
        "pct_alto": float((chla >= UMBRAL_CHLA_ALTO).mean() * 100) if chla.size else np.nan,
        "pct_fai_alto": float((fai > UMBRAL_FAI).mean() * 100) if fai.size else np.nan,
    }


def main() -> None:
    # Paso 1: calcular y guardar los índices de cada escena.
    for lago, fechas in FECHAS.items():
        print(f"=== {lago}: indices ===")
        for fecha in fechas:
            capas = calcular_indices(
                ruta_cruda(lago, fecha, "L1C"), ruta_cruda(lago, fecha, "L2A")
            )
            guardar_indices(lago, fecha, capas)
            print(f"  [ok] {fecha}")

    # Paso 2: máscara fija del lago y estadísticas por fecha.
    filas = []
    for lago, fechas in FECHAS.items():
        lago_mask = construir_mascara_lago(lago)
        print(f"{lago}: espejo de agua = {lago_mask.sum() * AREA_PIXEL_KM2:.1f} km2")
        for fecha in fechas:
            filas.append(resumen(lago, fecha, leer_indices(lago, fecha), lago_mask))

    tabla = pd.DataFrame(filas).sort_values(["lago", "fecha"]).reset_index(drop=True)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(DATA_PROCESSED / "estadisticas_por_fecha.csv", index=False)
    print(f"\nGuardado: {DATA_PROCESSED / 'estadisticas_por_fecha.csv'}")
    print(tabla)


if __name__ == "__main__":
    main()
