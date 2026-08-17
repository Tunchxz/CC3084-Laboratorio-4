# Laboratorio 4: Análisis de Datos GeoEspaciales

Detección y análisis de floraciones de cianobacterias en los lagos de **Atitlán** y **Amatitlán** (Guatemala) a partir de imágenes **Sentinel-2** del programa Copernicus, accedidas mediante el API **openEO**.

## Estructura

```
CC3084-Laboratorio-4/
├── src/
│   ├── config.py                           # coordenadas, fechas, bandas y rutas
│   ├── auth_openeo.py                      # autenticacion en Copernicus Data Space
│   ├── download_sentinel.py                # descarga de los recortes via openEO
│   ├── indices.py                          # NDVI, NDWI y custom script de cianobacteria
│   ├── procesar.py                         # genera los índices y la tabla de estadísticas
│   └── mapas.py                            # utilidades de visualización
├── notebooks/
│   ├── 01_obtencion_de_datos.ipynb         # ejercicios 1, 2 y 3
│   └── 02_analisis_cianobacteria.ipynb     # ejercicios 4 al 8
├── data/raw/                               # GeoTIFF descargados
├── data/processed/                         # índices calculados y estadísticas
├── requirements.txt
└── README.md
```

## Requisitos

- Python 3.14
- Una cuenta de [Copernicus Data Space](https://dataspace.copernicus.eu/)

## Instalación

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m ipykernel install --user \
    --name lab4-cc3084 --display-name "Python (Laboratorio 4)"
```

Los notebooks usan el kernel `lab4-cc3084`.

## Uso

1. **Autenticarse** (una sola vez; abre una página web para confirmar la identidad y guarda un token que luego se reutiliza):

```bash
.venv/bin/python src/auth_openeo.py
```

2. **Ejecutar los notebooks** en orden, desde la carpeta `notebooks/`:

   - `01_obtencion_de_datos.ipynb` descarga las 44 escenas (~550 MB) y genera los índices en `data/processed/`.
   - `02_analisis_cianobacteria.ipynb` realiza los análisis temporal, espacial, de
     correlación y comparativo.

   Los pasos de descarga y procesamiento también se pueden correr directamente:

   ```bash
   .venv/bin/python src/download_sentinel.py
   .venv/bin/python src/procesar.py
   ```
