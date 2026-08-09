"""
SUME DOCBLOCK

Nombre: gate
Tipo: Lógica

Entradas:
- Solicitudes concurrentes de acceso al emulador.

Acciones:
- Autoriza una única operación de interacción/observación cada vez.

Salidas:
- Contexto exclusivo o HarnessError EMULATOR_BUSY.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator
import asyncio

from contratos.mcp import HarnessError, McpErrorCode


class EmulatorOperationGate:
    """Own the single-operation invariant for the shared Android emulator."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    @property
    def is_busy(self) -> bool:
        """Expose whether another emulator operation owns the gate."""

        return self._lock.locked()

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[None]:
        """Grant exclusive access or reject immediately without queuing work."""

        if self._lock.locked():
            raise HarnessError(
                McpErrorCode.EMULATOR_BUSY,
                "Another emulator operation is already running.",
            )
        await self._lock.acquire()
        try:
            yield
        finally:
            self._lock.release()
