"""
SUME DOCBLOCK

Nombre: cliente_referencia
Tipo: Salida

Entradas:
- ReferenceRun terminado por el cliente MCP de referencia.

Acciones:
- Convierte el informe estructurado en JSON legible por terminal y automatización.

Salidas:
- Un único documento JSON; nunca texto de error no estructurado.
"""

from __future__ import annotations

import json

from contratos.cliente_referencia import ReferenceRun


def render_reference_run(run: ReferenceRun) -> str:
    """Print a stable report that names every MCP result and its evidence."""

    return json.dumps(run.to_dict(), ensure_ascii=False, indent=2)
