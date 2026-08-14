"""
SUME DOCBLOCK

Nombre: diagnostico
Tipo: Contrato

Entradas:
- Resultado de una comprobación de entorno.

Acciones:
- Define la forma estable de un diagnóstico y de su remedio.

Salidas:
- Check inmutable y serializable, sin dependencias de Android.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CheckState(StrEnum):
    """How a single environment check turned out."""

    OK = "OK"
    MISSING = "MISSING"
    # Not every piece is needed for every task: reading the code needs nothing,
    # the unit bank needs Python only, and just the live campaign needs a device.
    OPTIONAL = "OPTIONAL"


@dataclass(frozen=True)
class Check:
    """One thing the harness needs, and what to do when it is not there."""

    name: str
    state: CheckState
    detail: str
    remedy: str = ""

    @property
    def blocks_campaign(self) -> bool:
        """Whether this alone stops a real emulator campaign from running."""

        return self.state is CheckState.MISSING
