"""
SUME DOCBLOCK

Nombre: appium
Tipo: Lógica

Entradas:
- URL local del servidor Appium.

Acciones:
- Consulta la salud HTTP de Appium sin iniciar procesos ni sesiones.

Salidas:
- Versión de Appium disponible o HarnessError tipado.
"""

from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import urlopen

from contratos.mcp import HarnessError, McpErrorCode
from logica.seguridad.emulador import assert_local_appium_url


def read_appium_status(appium_url: str) -> dict[str, str]:
    """Read Appium status through its local status endpoint only."""

    assert_local_appium_url(appium_url)
    try:
        with urlopen(f"{appium_url.rstrip('/')}/status", timeout=5) as response:
            payload = json.load(response)
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise HarnessError(
            McpErrorCode.APPIUM_UNAVAILABLE,
            "Appium is unavailable at the configured local URL.",
        ) from exc
    version = payload.get("value", {}).get("build", {}).get("version")
    if not isinstance(version, str):
        raise HarnessError(
            McpErrorCode.APPIUM_UNAVAILABLE,
            "Appium returned an invalid status response.",
        )
    return {"appium_version": version}
