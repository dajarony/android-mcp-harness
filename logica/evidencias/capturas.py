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

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from contratos.mcp import HarnessError, McpErrorCode
from logica.evidencias.imagen import assert_png_shows_something


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts"

# Exactly the shape build_screenshot_path produces. Anything else is not an
# identifier this harness issued.
_ARTIFACT_ID = re.compile(r"^\d{8}-\d{6}-\d{6}-[a-z-]+\.png$")


def read_artifact_bytes(artifact_id: object) -> bytes:
    """Serve one evidence file by the identifier the harness itself handed out.

    The name is matched against the exact pattern this module writes and the
    resolved path is checked to stay inside artifacts/. A caller cannot walk out
    of the evidence directory, whatever it sends.
    """

    if not isinstance(artifact_id, str) or not _ARTIFACT_ID.fullmatch(artifact_id):
        raise HarnessError(
            McpErrorCode.EVIDENCE_WRITE_FAILED,
            "artifact_id is not an identifier issued by this harness.",
        )
    path = (ARTIFACTS / artifact_id).resolve()
    if path.parent != ARTIFACTS.resolve() or not path.is_file():
        raise HarnessError(
            McpErrorCode.EVIDENCE_WRITE_FAILED,
            "The requested evidence does not exist in the artifacts directory.",
        )
    return path.read_bytes()


def build_screenshot_path(label: str) -> Path:
    """Allocate a timestamped, local-only evidence path."""

    ARTIFACTS.mkdir(exist_ok=True)
    # The gate serializes emulator actions, but consecutive screenshots can still
    # arrive within one second. Microseconds preserve each operation's evidence.
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    return ARTIFACTS / f"{stamp}-{label}.png"


def save_screenshot(driver: Any, label: str) -> Path:
    """Persist one screenshot, refusing to keep a file that proves nothing."""

    path = build_screenshot_path(label)
    driver.save_screenshot(str(path))
    try:
        assert_png_shows_something(path.read_bytes(), "Appium")
    except HarnessError:
        # An empty capture is not evidence, and leaving it on disk would let a
        # later reader mistake it for one.
        path.unlink(missing_ok=True)
        raise
    return path


def save_png_artifact(payload: bytes, label: str) -> Path:
    """Persist trusted PNG bytes gathered by a fixed read-only adapter."""

    path = build_screenshot_path(label)
    path.write_bytes(payload)
    return path
