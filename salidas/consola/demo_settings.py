"""
SUME DOCBLOCK

Nombre: demo_settings
Tipo: Salida

Entradas:
- SettingsDemoResult normalizado.

Acciones:
- Convierte el resultado interno en texto de terminal.

Salidas:
- Mensaje de éxito o de error con la ruta de evidencia disponible.
"""

from __future__ import annotations

from contratos.demo_settings import SettingsDemoResult


def render_demo_result(result: SettingsDemoResult) -> str:
    """Format one result without changing business state."""

    prefix = "PASS" if result.succeeded else "FAIL"
    evidence = f"; screenshot: {result.screenshot_path}" if result.screenshot_path else ""
    return f"{prefix}: {result.detail}{evidence}"
