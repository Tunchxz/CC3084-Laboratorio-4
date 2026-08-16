"""Utilidades para visualizar los rasters en matplotlib y folium."""

from __future__ import annotations

import numpy as np
import rasterio
import matplotlib as mpl
from matplotlib import colors
from rasterio.warp import Resampling, calculate_default_transform, reproject


def extent_utm(ruta) -> tuple[float, float, float, float]:
    """Extension (left, right, bottom, top) para `plt.imshow(extent=...)`."""
    with rasterio.open(ruta) as src:
        b = src.bounds
    return (b.left, b.right, b.bottom, b.top)


def a_wgs84(array: np.ndarray, ruta) -> tuple[np.ndarray, list[list[float]]]:
    """Reproyecta un array a coordenadas geográficas (EPSG:4326).

    Devuelve el array reproyectado y los límites en el formato que espera
    `folium.raster_layers.ImageOverlay`: [[sur, oeste], [norte, este]].
    """
    with rasterio.open(ruta) as src:
        transform, ancho, alto = calculate_default_transform(
            src.crs, "EPSG:4326", src.width, src.height, *src.bounds
        )
        origen_crs, origen_transform = src.crs, src.transform

    destino = np.full((alto, ancho), np.nan, dtype="float32")
    reproject(
        source=array.astype("float32"),
        destination=destino,
        src_transform=origen_transform,
        src_crs=origen_crs,
        dst_transform=transform,
        dst_crs="EPSG:4326",
        resampling=Resampling.nearest,
        src_nodata=np.nan,
        dst_nodata=np.nan,
    )

    oeste, norte = transform * (0, 0)
    este, sur = transform * (ancho, alto)
    return destino, [[sur, oeste], [norte, este]]


def a_rgba(array: np.ndarray, vmin: float, vmax: float, cmap: str = "turbo") -> np.ndarray:
    """Convierte un array a una imagen RGBA con los NaN transparentes."""
    norma = colors.Normalize(vmin=vmin, vmax=vmax, clip=True)
    rgba = mpl.colormaps[cmap](norma(np.nan_to_num(array, nan=vmin)))
    rgba[..., 3] = np.where(np.isfinite(array), 1.0, 0.0)
    return rgba


def centro(ruta) -> list[float]:
    """Centro del raster en (lat, lon), útil para inicializar folium."""
    with rasterio.open(ruta) as src:
        from rasterio.warp import transform_bounds

        oeste, sur, este, norte = transform_bounds(src.crs, "EPSG:4326", *src.bounds)
    return [(sur + norte) / 2, (oeste + este) / 2]
