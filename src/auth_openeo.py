"""Autenticacion contra el backend openEO de Copernicus Data Space.

Ejecutar una sola vez desde la terminal:

    .venv/bin/python src/auth_openeo.py

Guarda el refresh token en el almacen local de openeo, de modo que los
notebooks puedan reconectarse con `authenticate_oidc()` sin volver a pedir
credenciales.
"""

import openeo

OPENEO_URL = "https://openeo.dataspace.copernicus.eu"


def main() -> None:
    connection = openeo.connect(OPENEO_URL)
    connection.authenticate_oidc_device(store_refresh_token=True)
    print("AUTH_OK")
    print(connection.describe_account())


if __name__ == "__main__":
    main()
