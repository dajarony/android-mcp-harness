"""
SUME DOCBLOCK

Nombre: maqueta
Tipo: Lógica

Entradas:
- Objetivos colocados, tamaño de pantalla y densidad Android.

Acciones:
- Mide defectos objetivos de área, límites y zona táctil.

Salidas:
- Hallazgos verificables de maqueta, sin juicios estéticos.
"""

from __future__ import annotations

from typing import Any

from logica.navegacion.arbol import Rectangle


MIN_TOUCH_TARGET_DP = 48


def layout_findings(
    entries: list[tuple[dict[str, Any], Rectangle]],
    screen: Rectangle,
    density: int | None,
) -> list[dict[str, Any]]:
    """Report layout defects a machine can prove, and only those."""

    minimum = round(MIN_TOUCH_TARGET_DP * density / 160) if density else None
    findings: list[dict[str, Any]] = []
    for entry, (left, top, right, bottom) in entries:
        width, height = right - left, bottom - top
        if width <= 0 or height <= 0:
            findings.append({"issue": "no_area", "selector": entry["selector"]})
            continue
        if left < screen[0] or top < screen[1] or right > screen[2] or bottom > screen[3]:
            findings.append({"issue": "off_screen", "selector": entry["selector"]})
        if minimum and width < minimum and height < minimum:
            findings.append(
                {
                    "issue": "touch_target_too_small",
                    "selector": entry["selector"],
                    "size_px": [width, height],
                    "minimum_px": minimum,
                }
            )
    return findings


def overlaps(rectangle: Rectangle, region: Rectangle) -> bool:
    """Whether two rectangles share any area at all."""

    left, top, right, bottom = rectangle
    return not (
        right <= region[0] or left >= region[2] or bottom <= region[1] or top >= region[3]
    )
