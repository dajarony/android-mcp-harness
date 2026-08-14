"""
SUME DOCBLOCK

Nombre: doctor
Tipo: Entrada

Entradas:
- Variables APPIUM_URL, ANDROID_UDID y ANDROID_MCP_CONNECT_TIMEOUT.

Acciones:
- Ejecuta el diagnóstico de entorno y lo imprime.

Salidas:
- Informe en terminal y código de proceso según lo que falte.
"""

from __future__ import annotations

from entradas.comandos.demo_settings import load_config_from_environment
from logica.diagnostico.entorno import inspect_environment
from salidas.consola.doctor import render_diagnosis


def main() -> int:
    """Report what the harness needs and what is missing, without guessing."""

    checks = inspect_environment(load_config_from_environment())
    print(render_diagnosis(checks))
    return 1 if any(check.blocks_campaign for check in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
