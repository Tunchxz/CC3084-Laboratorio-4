"""Calculo local de indices espectrales a partir de las bandas descargadas.

NDVI = (B08 - B04) / (B08 + B04)
NDWI = (B03 - B08) / (B03 + B08)   (McFeeters, 1996)
"""
import numpy as np
import rasterio


def _safe_div(numerador, denominador):
    with np.errstate(divide="ignore", invalid="ignore"):
        resultado = numerador / denominador
    resultado[~np.isfinite(resultado)] = np.nan
    return resultado


def leer_bandas(tif_path, orden_bandas=("B03", "B04", "B08")):
    """Lee un GeoTIFF multibanda (orden segun BANDAS_REQUERIDAS) y devuelve un
    dict {nombre_banda: array float32}, junto con el perfil rasterio (para
    poder reescribir resultados georreferenciados).
    """
    with rasterio.open(tif_path) as src:
        perfil = src.profile
        arrays = {
            nombre: src.read(i + 1).astype("float32")
            for i, nombre in enumerate(orden_bandas)
        }
    return arrays, perfil


def calcular_ndvi(b04, b08):
    return _safe_div(b08 - b04, b08 + b04)


def calcular_ndwi(b03, b08):
    return _safe_div(b03 - b08, b03 + b08)


def calcular_ndvi_ndwi_desde_tif(tif_path, orden_bandas=("B03", "B04", "B08")):
    """Atajo: lee el GeoTIFF de bandas de un lago/fecha y devuelve (ndvi, ndwi, perfil)."""
    arrays, perfil = leer_bandas(tif_path, orden_bandas)
    ndvi = calcular_ndvi(arrays["B04"], arrays["B08"])
    ndwi = calcular_ndwi(arrays["B03"], arrays["B08"])
    return ndvi, ndwi, perfil
