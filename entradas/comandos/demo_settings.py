"""
SUME DOCBLOCK

Nombre: demo_settings
Tipo: Entrada

Entradas:
- Variables APPIUM_URL y ANDROID_UDID del entorno local.

Acciones:
- Construye el contrato de configuración e invoca el controlador de la demo.

Salidas:
- Código de proceso y texto de resultado para la terminal.
"""

from __future__ import annotations

import os

from contratos.demo_settings import SettingsDemoConfig
from logica.controladores.demo_settings import run_settings_demo
from salidas.consola.demo_settings import render_demo_result


def load_config_from_environment() -> SettingsDemoConfig:
    """Read the two supported local connection variables."""

    return SettingsDemoConfig(
        appium_url=os.getenv("APPIUM_URL", "http://127.0.0.1:4723"),
        udid=os.getenv("ANDROID_UDID", "emulator-5554"),
        connect_timeout_seconds=int(os.getenv("ANDROID_MCP_CONNECT_TIMEOUT", "120")),
    )


def main() -> int:
    """Run the Settings -> Apps command and expose its process status."""

    config = load_config_from_environment()
    print(f"Connecting to {config.appium_url} on {config.udid}...")
    result = run_settings_demo(config)
    print(render_demo_result(result))
    return 0 if result.succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
