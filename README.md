# Laboratorio 4 — Análisis de Datos GeoEspaciales

CC3084 – Data Science, UVG. Detección de floraciones de cianobacteria en los
lagos de Atitlán y Amatitlán usando imágenes Sentinel-2 (Copernicus Data
Space Ecosystem) y el script oficial de cianobacteria de
[custom-scripts.sentinel-hub.com](https://custom-scripts.sentinel-hub.com).

## Estructura

```
├── src/                 # módulos de conexión, descarga y cálculo de índices
│   ├── config.py         # bbox de cada lago, fechas oficiales, bandas requeridas
│   ├── sentinel_api.py    # conexión openEO + Sentinel Hub Process API
│   ├── indices.py         # cálculo local de NDVI y NDWI
│   └── evalscripts/       # script oficial de cianobacteria (visual y analítico)
├── notebooks/
│   ├── 01_conexion_y_descarga.ipynb        # Ejercicios 1-2
│   └── 02_indices_y_analisis_temporal.ipynb # Ejercicios 3-4 (resto en progreso)
├── data/raw/             # datos crudos descargados (GeoTIFF, no se versionan) + geojson de cada lago
├── data/processed/       # CSVs y figuras generadas (reproducibles, no se versionan)
├── docs/                 # informe final .pdf dirigido a ambientalistas
├── requirements.txt
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # o .venv\Scripts\activate en Windows
pip install -r requirements.txt
```

Crea un archivo `.env` (basado en `.env.example`) con tus credenciales OAuth
de Copernicus Data Space Ecosystem:

```
SH_CLIENT_ID=...
SH_CLIENT_SECRET=...
```

Genera esas credenciales en https://dataspace.copernicus.eu (cuenta gratuita)
→ https://shapps.dataspace.copernicus.eu/dashboard/#/account/settings →
pestaña "OAuth clients" → "+ Create new".

## Uso

1. `notebooks/01_conexion_y_descarga.ipynb` — conecta a la API y descarga,
   para cada lago y cada una de las 11 fechas oficiales del enunciado, las
   bandas necesarias para NDVI/NDWI y el resultado del script de
   cianobacteria.
2. `notebooks/02_indices_y_analisis_temporal.ipynb` — calcula los índices,
   arma la tabla `lago x fecha x índice` y grafica la evolución temporal del
   índice de cianobacteria.

## Datos

Las coordenadas (bbox) y fechas oficiales de cada lago están fijadas en
`src/config.py`, tal como se especifican en el enunciado del laboratorio
(`Laboratorio 4. Datos Geoespaciales. 2026.pdf`), para asegurar que todos los
grupos trabajen con la misma base de imágenes.
