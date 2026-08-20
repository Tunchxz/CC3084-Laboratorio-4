"""Construccion del dataset tabular para los modelos de Machine Learning.

Convierte los rasters de la Parte 1 en una tabla donde cada fila es un pixel de
20 m dentro del espejo de agua de un lago, en una fecha concreta.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import rasterio
from scipy import ndimage

import indices as ix
import procesar
from config import (
    DATA_PROCESSED,
    ESCALA_REFLECTANCIA,
    FECHAS,
    NUBOSIDAD,
    RESOLUCION_M,
)

# --------------------------------------------------------------------------
# Definición de la variable respuesta
# --------------------------------------------------------------------------
# Umbral de clorofila-a (mg/m3) que separa "alta presencia" de "ausencia o baja
# presencia". Corresponde a la frontera entre riesgo bajo y moderado de la OMS
# (Guidelines on Recreational Water Quality, Vol. 1, 2021) para agua recreativa
# con dominancia de cianobacteria, y coincide aproximadamente con el límite
# eutrófico de la OECD (1982) y con el TSI = 50 de Carlson (1977).
UMBRAL_CHLA_OMS = 10.0

# --------------------------------------------------------------------------
# Variables
# --------------------------------------------------------------------------
IDENTIFICADORES = [
    "lago",
    "fecha",
    "fila",
    "columna",
    "x_utm",
    "y_utm",
    "bloque_1km",
]

# Bandas espectrales que SI pueden ser predictoras: ninguna interviene en NDCI.
BANDAS_PREDICTORAS = ["B02", "B03", "B07", "B08", "B8A", "B11", "B12"]

# Índices construidos solo con bandas limpias.
INDICES_LIMPIOS = ["ndwi", "mndwi", "ndmi"]

PREDICTORES = BANDAS_PREDICTORAS + INDICES_LIMPIOS + [
    "distancia_orilla_m",
    "mes",
    "estacion_lluviosa",
]

# Variables que no pueden usarse como predictoras porque participan, directa o
# indirectamente, en la construcción de `y_alta`.
EXCLUIDAS_POR_FUGA = ["B04", "B05", "ndci", "ndvi", "fai", "chla"]

# Metadato de diagnóstico: es constante dentro de una escena, así que como
# predictor actuaría de identificador de fecha.
CONTEXTO = ["nubosidad_pct"]

RESPUESTA = "y_alta"

COLUMNAS = IDENTIFICADORES + PREDICTORES + EXCLUIDAS_POR_FUGA + CONTEXTO + [RESPUESTA]

# Tipos declarados, para que el dataset leido desde CSV conserve exactamente los
# mismos tipos con los que se construyó (el CSV no los guarda).
DTIPOS: dict[str, str] = {
    "lago": "object",
    "fila": "int16",
    "columna": "int16",
    "x_utm": "float64",
    "y_utm": "float64",
    "bloque_1km": "object",
    "mes": "int8",
    "estacion_lluviosa": "int8",
    "nubosidad_pct": "float32",
    RESPUESTA: "int8",
}
DTIPOS.update(
    {
        col: "float32"
        for col in BANDAS_PREDICTORAS + INDICES_LIMPIOS + ["distancia_orilla_m"]
        + EXCLUIDAS_POR_FUGA
    }
)

# Todas las bandas que hay que leer del GeoTIFF crudo.
BANDAS_LEIDAS = BANDAS_PREDICTORAS + ["B04", "B05"]

# --------------------------------------------------------------------------
# Muestreo y bloques espaciales
# --------------------------------------------------------------------------
# Fracción idéntica en las 22 escenas: preserva la prevalencia global, la
# proporción entre lagos y la estructura por fecha.
FRACCION_MUESTRA = 0.107
SEMILLA = 42

# Lado de los bloques de la validación espacial, en metros.
TAMANO_BLOQUE_M = 1000

# Meses de la estación lluviosa en Guatemala.
MESES_LLUVIOSOS = (5, 6, 7, 8, 9, 10)

RUTA_DATASET = DATA_PROCESSED / "dataset_ml.csv"


def distancia_orilla(mascara: np.ndarray) -> np.ndarray:
    """Distancia de cada pixel de agua al borde del espejo de agua, en metros.

    Es la única variable espacial que se usa como predictora. A diferencia de
    las coordenadas crudas, no permite memorizar ubicaciones concretas, resume
    una propiedad fisica (cuan adentro del lago esta el pixel) que se relaciona
    con la profundidad, la mezcla del agua y la cercanía a los aportes de la
    cuenca.
    """
    return ndimage.distance_transform_edt(mascara) * RESOLUCION_M


def asignar_bloques(
    lago: str, x_utm: np.ndarray, y_utm: np.ndarray, tamano: int = TAMANO_BLOQUE_M
) -> np.ndarray:
    """Identificador del bloque espacial de cada observación.

    Los bloques se trazan sobre una rejilla absoluta en coordenadas UTM, asi que
    un mismo pixel cae siempre en el mismo bloque en todas las fechas. Eso es lo
    que permite que `GroupKFold` mantenga juntas todas las observaciones de una
    misma zona.
    """
    bx = np.floor_divide(x_utm, tamano).astype(int)
    by = np.floor_divide(y_utm, tamano).astype(int)
    return np.char.add(f"{lago}_", np.char.add(bx.astype(str), np.char.add("_", by.astype(str))))


def _bandas_crudas(lago: str, fecha: str) -> dict[str, np.ndarray]:
    """Bandas espectrales del producto L1C en reflectancia 0-1.

    Se lee solo el L1C. La máscara de nubes ya viene resuelta en la capa
    `validos` del GeoTIFF de índices, así que no hace falta abrir el L2A.

    La corrección radiométrica deja algunos valores negativos, que no tienen
    sentido físico como reflectancia; se recortan en 0.
    """
    capas = ix._leer(procesar.ruta_cruda(lago, fecha, "L1C"))
    return {
        nombre: np.clip(capas[nombre] / ESCALA_REFLECTANCIA, 0, None)
        for nombre in BANDAS_LEIDAS
    }


def tabla_escena(lago: str, fecha: str) -> pd.DataFrame:
    """Tabla con una fila por pixel válido del lago en una fecha.

    Se conservan únicamente los pixeles que estan dentro de la máscara fija del
    espejo de agua, que no son nube ni sombra según SCL (`validos`), y que tienen
    valor finito en las 13 variables predictoras.
    """
    mascara = procesar.leer_mascara_lago(lago)
    capas = procesar.leer_indices(lago, fecha)
    bandas = _bandas_crudas(lago, fecha)

    # Índices adicionales, construidos solo con bandas ajenas a NDCI.
    mndwi = ix._normalizado(bandas["B03"], bandas["B11"])
    ndmi = ix._normalizado(bandas["B08"], bandas["B11"])

    usable = mascara & capas["validos"]

    # Se exige valor finito en los 13 predictores y también en `chla`: un pixel
    # sin clorofila-a definida no tiene variable respuesta, y dejarlo pasar lo
    # etiquetaría como clase 0 en silencio (NaN > umbral es False).
    finitos = np.isfinite(mndwi) & np.isfinite(ndmi) & np.isfinite(capas["ndwi"])
    finitos &= np.isfinite(capas["chla"])
    for nombre in BANDAS_PREDICTORAS:
        finitos &= np.isfinite(bandas[nombre])
    usable &= finitos

    filas, columnas = np.nonzero(usable)

    with rasterio.open(procesar.ruta_indices(lago, fecha)) as src:
        transformacion = src.transform
    x_utm, y_utm = transformacion * (columnas + 0.5, filas + 0.5)
    x_utm = np.asarray(x_utm)
    y_utm = np.asarray(y_utm)

    marca = pd.Timestamp(fecha)
    distancias = distancia_orilla(mascara)

    datos: dict[str, np.ndarray] = {
        "lago": np.full(filas.size, lago),
        "fecha": np.full(filas.size, marca),
        "fila": filas.astype(np.int16),
        "columna": columnas.astype(np.int16),
        "x_utm": x_utm,
        "y_utm": y_utm,
        "bloque_1km": asignar_bloques(lago, x_utm, y_utm),
    }
    for nombre in BANDAS_PREDICTORAS:
        datos[nombre] = bandas[nombre][usable].astype(np.float32)
    datos["ndwi"] = capas["ndwi"][usable].astype(np.float32)
    datos["mndwi"] = mndwi[usable].astype(np.float32)
    datos["ndmi"] = ndmi[usable].astype(np.float32)
    datos["distancia_orilla_m"] = distancias[usable].astype(np.float32)
    datos["mes"] = np.full(filas.size, marca.month, dtype=np.int8)
    datos["estacion_lluviosa"] = np.full(
        filas.size, int(marca.month in MESES_LLUVIOSOS), dtype=np.int8
    )
    for nombre in ("B04", "B05"):
        datos[nombre] = bandas[nombre][usable].astype(np.float32)
    for nombre in ("ndci", "ndvi", "fai", "chla"):
        datos[nombre] = capas[nombre][usable].astype(np.float32)
    datos["nubosidad_pct"] = np.full(
        filas.size, NUBOSIDAD[lago][fecha], dtype=np.float32
    )
    datos[RESPUESTA] = (datos["chla"] > UMBRAL_CHLA_OMS).astype(np.int8)

    return pd.DataFrame(datos, columns=COLUMNAS)


def matriz_escena(lago: str, fecha: str) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """Predictores de todos los pixeles válidos de una escena, con su posición.

    Devuelve `(X, filas, columnas)` para poder reinsertar las predicciones en la
    malla del ráster y dibujar el mapa predictivo.
    """
    tabla = tabla_escena(lago, fecha)
    return (
        tabla[PREDICTORES].reset_index(drop=True),
        tabla["fila"].to_numpy(),
        tabla["columna"].to_numpy(),
    )


def muestrear_escena(
    lago: str,
    fecha: str,
    fraccion: float = FRACCION_MUESTRA,
    semilla: int = SEMILLA,
) -> pd.DataFrame:
    """Muestra aleatoria de una escena, con la misma fracción en todas."""
    tabla = tabla_escena(lago, fecha)
    return tabla.sample(frac=fraccion, random_state=semilla)


def construir_dataset(
    fraccion: float = FRACCION_MUESTRA,
    semilla: int = SEMILLA,
    verbose: bool = True,
) -> pd.DataFrame:
    """Construye la muestra de las 22 escenas y la escribe en CSV."""
    partes = []
    for lago, fechas in FECHAS.items():
        for fecha in fechas:
            parte = muestrear_escena(lago, fecha, fraccion, semilla)
            partes.append(parte)
            if verbose:
                print(
                    f"  [ok] {lago:10s} {fecha}  "
                    f"{len(parte):>6,} filas  {int(parte[RESPUESTA].sum()):>5,} positivos"
                )

    dataset = pd.concat(partes, ignore_index=True)
    RUTA_DATASET.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(RUTA_DATASET, index=False, float_format="%.7g")
    if verbose:
        tam_mb = RUTA_DATASET.stat().st_size / 1e6
        print(f"\nGuardado: {RUTA_DATASET} ({tam_mb:.1f} MB, {len(dataset):,} filas)")
    return dataset


def cargar_dataset() -> pd.DataFrame:
    """Lee el dataset ya construido desde `data/processed/dataset_ml.csv`."""
    return pd.read_csv(RUTA_DATASET, parse_dates=["fecha"], dtype=DTIPOS)


def estadisticas_poblacion() -> pd.DataFrame:
    """Conteos sobre la población completa, sin materializarla en memoria.

    Recorre las 22 escenas acumulando solo totales, de modo que los números de
    los ejercicios 1.4, 2.3 y 2.4 se reportan sobre los 3.76 millones de
    observaciones y no sobre la muestra.
    """
    filas = []
    for lago, fechas in FECHAS.items():
        mascara = procesar.leer_mascara_lago(lago)
        for fecha in fechas:
            tabla = tabla_escena(lago, fecha)
            chla = tabla["chla"].to_numpy()
            filas.append(
                {
                    "lago": lago,
                    "fecha": pd.Timestamp(fecha),
                    "pixeles_lago": int(mascara.sum()),
                    "observaciones": len(tabla),
                    "cobertura_pct": len(tabla) / mascara.sum() * 100,
                    "positivos": int((chla > UMBRAL_CHLA_OMS).sum()),
                    "prevalencia_pct": float((chla > UMBRAL_CHLA_OMS).mean() * 100),
                    "chla_media": float(chla.mean()),
                    "chla_p90": float(np.percentile(chla, 90)),
                }
            )
    return pd.DataFrame(filas)


def main() -> None:
    print(f"Umbral de respuesta: chla > {UMBRAL_CHLA_OMS} mg/m3 (OMS)")
    print(f"Predictores ({len(PREDICTORES)}): {', '.join(PREDICTORES)}")
    print(f"Excluidas por fuga: {', '.join(EXCLUIDAS_POR_FUGA)}\n")
    construir_dataset()


if __name__ == "__main__":
    main()
