"""Calculo local de NDVI, NDWI y del índice de cianobacteria.

El índice de cianobacteria replica el custom script "CyanoLakes Chlorophyll-a" publicado en
https://custom-scripts.sentinel-hub.com/custom-scripts/sentinel-2/cyanobacteria_chla_ndci_l1c/
(Kravitz & Matthews, 2020), que combina:

* una máscara de agua (`wbi`) construida con varios índices de agua,
* el índice NDCI = (B05 - B04) / (B05 + B04), sensible a la clorofila-a,
* la conversion polinomial de NDCI a clorofila-a en mg/m3,
* el índice FAI, que marca floraciones flotantes en superficie.

Las bandas espectrales se leen del producto L1C (que es para el que fue escrito
el script) y la banda SCL del producto L2A, usada solo para descartar nubes.
"""

from __future__ import annotations

import numpy as np
import rasterio

from config import ESCALA_REFLECTANCIA

# Clases de la banda SCL que se descartan: sin dato, saturado, sombra de nube,
# nube (probabilidad media y alta) y cirros delgados.
SCL_INVALIDAS = (0, 1, 3, 8, 9, 10)

# Umbrales del custom script
MNDWI_THRESHOLD = 0.42
NDWI_THRESHOLD = 0.4
FAI_THRESHOLD = 0.08


def _div(numerador: np.ndarray, denominador: np.ndarray) -> np.ndarray:
    """División segura: devuelve NaN donde el denominador es cero."""
    return np.divide(
        numerador,
        denominador,
        out=np.full_like(numerador, np.nan, dtype=np.float32),
        where=denominador != 0,
    )


def _normalizado(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Diferencia normalizada (a - b) / (a + b) acotada al rango [-1, 1].

    La corrección atmosferica de Sentinel-2 L2A puede dejar reflectancias
    negativas en algunos pixeles; ahi el cociente se dispara fuera de su rango
    teórico, por lo que esos pixeles se marcan como NaN.
    """
    valido = (a > 0) & (b > 0)
    resultado = _div(a - b, a + b)
    return np.where(valido, resultado, np.nan)


def _leer(ruta) -> dict[str, np.ndarray]:
    """Lee un GeoTIFF multibanda como diccionario {nombre_banda: array}."""
    with rasterio.open(ruta) as src:
        datos = src.read().astype(np.float32)
        nodata = src.nodata
        nombres = list(src.descriptions)

    capas: dict[str, np.ndarray] = {}
    for i, nombre in enumerate(nombres):
        capa = datos[i]
        if nodata is not None:
            capa = np.where(capa == nodata, np.nan, capa)
        capas[nombre] = capa
    return capas


def leer_bandas(ruta_l1c, ruta_l2a) -> dict[str, np.ndarray]:
    """Lee las bandas L1C en reflectancia (0-1) y la banda SCL del L2A."""
    bandas = {
        nombre: capa / ESCALA_REFLECTANCIA for nombre, capa in _leer(ruta_l1c).items()
    }
    bandas["SCL"] = _leer(ruta_l2a)["SCL"]
    return bandas


def leer_perfil(ruta) -> dict:
    """Devuelve el perfil (CRS, transform, tamano) del GeoTIFF."""
    with rasterio.open(ruta) as src:
        return {
            "crs": src.crs,
            "transform": src.transform,
            "bounds": src.bounds,
            "height": src.height,
            "width": src.width,
        }


def mascara_valida(bandas: dict[str, np.ndarray]) -> np.ndarray:
    """Pixeles utilizables: con dato y sin nube ni sombra según SCL."""
    scl = bandas["SCL"]
    con_dato = ~np.isnan(bandas["B04"]) & ~np.isnan(scl)
    sin_nube = ~np.isin(scl, SCL_INVALIDAS)
    return con_dato & sin_nube


def ndvi(bandas: dict[str, np.ndarray]) -> np.ndarray:
    """NDVI = (B08 - B04) / (B08 + B04)."""
    return _normalizado(bandas["B08"], bandas["B04"])


def ndwi(bandas: dict[str, np.ndarray]) -> np.ndarray:
    """NDWI = (B03 - B08) / (B03 + B08)."""
    return _normalizado(bandas["B03"], bandas["B08"])


def ndci(bandas: dict[str, np.ndarray]) -> np.ndarray:
    """NDCI = (B05 - B04) / (B05 + B04). Base del índice de cianobacteria."""
    return _normalizado(bandas["B05"], bandas["B04"])


def fai(bandas: dict[str, np.ndarray]) -> np.ndarray:
    """FAI = B07 - B04 - (B8A - B04) * (783-665) / (865-665)."""
    rojo, b07, b8a = bandas["B04"], bandas["B07"], bandas["B8A"]
    return b07 - rojo - (b8a - rojo) * (783 - 665) / (865 - 665)


def clorofila_a(indice_ndci: np.ndarray) -> np.ndarray:
    """Convierte NDCI a clorofila-a (mg/m3) con el polinomio del custom script.

    El polinomio puede dar valores negativos cuando el NDCI es muy bajo; como
    una concentración negativa no tiene sentido físico, se recorta en 0.
    """
    chla = (
        826.57 * indice_ndci**3
        - 176.43 * indice_ndci**2
        + 19 * indice_ndci
        + 4.071
    )
    return np.clip(chla, 0, None)


def mascara_agua(bandas: dict[str, np.ndarray]) -> np.ndarray:
    """Máscara de agua `wbi` del custom script de cianobacteria."""
    azul, verde, rojo = bandas["B02"], bandas["B03"], bandas["B04"]
    nir, swir1, swir2 = bandas["B08"], bandas["B11"], bandas["B12"]

    indice_vegetacion = _div(nir - rojo, nir + rojo)
    mndwi = _div(verde - swir1, verde + swir1)
    indice_agua = _div(verde - nir, verde + nir)
    ndwi_hojas = _div(nir - swir1, nir + swir1)
    aweish = azul + 2.5 * verde - 1.5 * (nir + swir1) - 0.25 * swir2
    aweinsh = 4 * (verde - swir1) - (0.25 * nir + 2.75 * swir1)
    dbsi = _div(swir1 - verde, swir1 + verde) - indice_vegetacion

    es_agua = (
        (mndwi > MNDWI_THRESHOLD)
        | (indice_agua > NDWI_THRESHOLD)
        | (aweinsh > 0.1879)
        | (aweish > 0.1112)
        | (indice_vegetacion < -0.2)
        | (ndwi_hojas > 1)
    )
    # filter_UABS: descarta zonas urbanas y suelo desnudo mal clasificadas
    es_agua = es_agua & ~((aweinsh <= -0.03) | (dbsi > 0))
    return np.where(np.isnan(rojo), False, es_agua)


def calcular_indices(ruta_l1c, ruta_l2a) -> dict[str, np.ndarray]:
    """Calcula todas las capas derivadas de una escena.

    Devuelve NDVI, NDWI, NDCI, FAI y clorofila-a para toda la escena, mas dos
    máscaras booleanas: `agua` (pixeles de agua segun el custom script, ya sin
    nubes) y `validos` (pixeles sin nube ni sombra según SCL).
    """
    bandas = leer_bandas(ruta_l1c, ruta_l2a)
    validos = mascara_valida(bandas)

    capas = {
        "ndvi": ndvi(bandas),
        "ndwi": ndwi(bandas),
        "ndci": ndci(bandas),
        "fai": fai(bandas),
    }
    capas["chla"] = clorofila_a(capas["ndci"])
    capas["agua"] = mascara_agua(bandas) & validos
    capas["validos"] = validos
    return capas
