"""
SUME DOCBLOCK

Nombre: doctor
Tipo: Salida

Entradas:
- Lista de Check producida por el diagnóstico de entorno.

Acciones:
- Convierte el diagnóstico en un informe de terminal legible.

Salidas:
- Texto con un renglón por comprobación y los remedios pendientes.
"""

from __future__ import annotations

from contratos.diagnostico import Check, CheckState


_MARK = {CheckState.OK: "ok  ", CheckState.MISSING: "MISS", CheckState.OPTIONAL: "--  "}


def render_diagnosis(checks: list[Check]) -> str:
    """Format the whole picture, then only the remedies that are still needed."""

    width = max(len(check.name) for check in checks)
    lines = [f"[{_MARK[check.state]}] {check.name:<{width}}  {check.detail}" for check in checks]

    blocking = [check for check in checks if check.blocks_campaign]
    optional = [check for check in checks if check.state is CheckState.OPTIONAL]

    if blocking:
        lines.append("")
        lines.append(f"{len(blocking)} of {len(checks)} checks block a real campaign:")
        lines.extend(f"  {check.name}: {check.remedy}" for check in blocking)
        lines.append("")
        lines.append(
            "The unit bank does not need any of this: "
            "python -m unittest discover -s tests"
        )
    else:
        lines.append("")
        lines.append("Everything a real campaign needs is present.")
        lines.extend(f"  optional - {check.name}: {check.remedy}" for check in optional)

    return "\n".join(lines)
