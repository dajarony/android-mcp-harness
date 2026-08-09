"""
SUME DOCBLOCK

Nombre: capturas
Tipo: Lógica

Entradas:
- Driver Appium y una etiqueta de evidencia.

Acciones:
- Construye una ruta local de evidencia y guarda una captura.

Salidas:
- Ruta absoluta de la captura creada dentro de artifacts/.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts"


def build_screenshot_path(label: str) -> Path:
    """Allocate a timestamped, local-only evidence path."""

    ARTIFACTS.mkdir(exist_ok=True)
    # The gate serializes emulator actions, but consecutive screenshots can still
    # arrive within one second. Microseconds preserve each operation's evidence.
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    return ARTIFACTS / f"{stamp}-{label}.png"


def save_screenshot(driver: Any, label: str) -> Path:
    """Persist one screenshot and return its absolute path."""

    path = build_screenshot_path(label)
    driver.save_screenshot(str(path))
    return path


def save_png_artifact(payload: bytes, label: str) -> Path:
    """Persist trusted PNG bytes gathered by a fixed read-only adapter."""

    path = build_screenshot_path(label)
    path.write_bytes(payload)
    return path
