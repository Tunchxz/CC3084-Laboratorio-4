"""Conexion a Copernicus Data Space Ecosystem y descarga de datos Sentinel-2.

Dos vias, ambas usando las mismas credenciales OAuth (Sentinel Hub / openEO):

1. openEO (`get_openeo_connection`, `descargar_bandas`): descarga unicamente
   las bandas B03, B04, B08 necesarias para NDVI y NDWI, para cada lago y
   fecha oficial del laboratorio.
2. Sentinel Hub Process API (`get_sh_config`, `descargar_cyano`): ejecuta
   directamente el script oficial de cianobacteria (ver src/evalscripts/) y
   descarga su resultado, sin descargar bandas completas de mas.

Credenciales: definir las variables de entorno
    SH_CLIENT_ID
    SH_CLIENT_SECRET
"""
import os
from pathlib import Path

from src.config import DATA_RAW, LAGOS, OPENEO_BACKEND_URL

EVALSCRIPTS_DIR = Path(__file__).resolve().parent / "evalscripts"


def get_openeo_connection():
    """Conecta y autentica contra el backend openEO de Copernicus Data Space.

    Usa client credentials (SH_CLIENT_ID / SH_CLIENT_SECRET) si estan
    definidas como variables de entorno; si no, cae a login interactivo por
    navegador (authenticate_oidc), que debe ejecutarse localmente en Jupyter.
    """
    import openeo

    con = openeo.connect(OPENEO_BACKEND_URL)

    client_id = os.getenv("SH_CLIENT_ID")
    client_secret = os.getenv("SH_CLIENT_SECRET")

    if client_id and client_secret:
        con.authenticate_oidc_client_credentials(
            client_id=client_id, client_secret=client_secret
        )
    else:
        # Requiere completar el login en el navegador que se abre; solo
        # funciona en una sesion interactiva local, no de forma automatizada.
        con.authenticate_oidc()

    return con


def descargar_bandas(con, lago: str, fecha: str, bandas=None, out_dir: Path = None) -> Path:
    """Descarga las bandas minimas (por defecto B03, B04, B08) de un lago en
    una fecha puntual, recortadas a su bbox, y las guarda como GeoTIFF en
    data/raw/<lago>/<fecha>_bandas.tif. Devuelve la ruta del archivo.
    """
    from src.config import BANDAS_REQUERIDAS

    bandas = bandas or BANDAS_REQUERIDAS
    bbox = LAGOS[lago]["bbox"]
    out_dir = out_dir or (DATA_RAW / lago)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{fecha}_bandas.tif"

    if out_path.exists():
        return out_path

    cube = con.load_collection(
        "SENTINEL2_L2A",
        spatial_extent=bbox,
        temporal_extent=[fecha, fecha],
        bands=bandas,
        max_cloud_cover=15,
    )
    cube = cube.max_time()  # colapsa a un solo mosaico para esa fecha
    cube.download(str(out_path), format="GTiff")
    return out_path


def get_sh_config():
    """Configura sentinelhub-py con las mismas credenciales OAuth."""
    from sentinelhub import SHConfig

    config = SHConfig()
    config.sh_client_id = os.environ["SH_CLIENT_ID"]
    config.sh_client_secret = os.environ["SH_CLIENT_SECRET"]
    config.sh_base_url = "https://sh.dataspace.copernicus.eu"
    config.sh_token_url = (
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    )
    return config


def descargar_cyano(lago: str, fecha: str, out_dir: Path = None, resolution: int = 20) -> Path:
    """Ejecuta el script oficial de cianobacteria (version analitica, float32)
    contra el Process API de Sentinel Hub para un lago y fecha, y guarda el
    resultado (chl_a, water_mask, FAI, dataMask) como GeoTIFF en
    data/raw/<lago>/<fecha>_cyano.tif.
    """
    from sentinelhub import (
        BBox,
        CRS,
        DataCollection,
        MimeType,
        SentinelHubRequest,
        bbox_to_dimensions,
    )

    bbox_dict = LAGOS[lago]["bbox"]
    bbox = BBox(
        (bbox_dict["west"], bbox_dict["south"], bbox_dict["east"], bbox_dict["north"]),
        crs=CRS.WGS84,
    )
    size = bbox_to_dimensions(bbox, resolution=resolution)

    evalscript = (EVALSCRIPTS_DIR / "cyano_ndci_l1c_analytical.js").read_text()

    out_dir = out_dir or (DATA_RAW / lago)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{fecha}_cyano.tif"

    if out_path.exists():
        return out_path

    config = get_sh_config()
    # El script oficial se llama "...NDCI_L1C": sus coeficientes (NDCI -> chl-a,
    # umbrales de wbi/FAI) fueron calibrados sobre reflectancia TOA (L1C), no
    # sobre reflectancia de superficie (L2A). Usar L2A aqui sesga el modelo y
    # produce valores extremos espurios en algunas fechas (nubes delgadas,
    # glint). Ademas, DataCollection.SENTINEL2_L1C por defecto apunta a
    # services.sentinel-hub.com; para Copernicus Data Space Ecosystem hay que
    # redefinirla con su service_url.
    coleccion_cdse = DataCollection.SENTINEL2_L1C.define_from(
        "SENTINEL2_L1C_CDSE", service_url=config.sh_base_url
    )
    request = SentinelHubRequest(
        evalscript=evalscript,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=coleccion_cdse,
                time_interval=(fecha, fecha),
                mosaicking_order="leastCC",
            )
        ],
        responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
        bbox=bbox,
        size=size,
        config=config,
    )
    data = request.get_data(save_data=False)[0]

    import rasterio
    from rasterio.transform import from_bounds

    transform = from_bounds(*bbox, width=size[0], height=size[1])
    with rasterio.open(
        out_path,
        "w",
        driver="GTiff",
        height=size[1],
        width=size[0],
        count=4,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        for i in range(4):
            dst.write(data[:, :, i], i + 1)
        dst.descriptions = ("chl_a_ugL", "water_mask", "FAI", "dataMask")

    return out_path
