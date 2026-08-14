"""
SUME DOCBLOCK

Nombre: flujo
Tipo: Lógica

Entradas:
- Configuración Appium, sesión opaca de flujo y operaciones UI serializadas.

Acciones:
- Conserva un driver únicamente para una cadena explícita, con caducidad y cierre.

Salidas:
- Driver exclusivo o HarnessError tipado; nunca una sesión huérfana permanente.
"""

from __future__ import annotations

import asyncio
import re
import secrets
from contextlib import asynccontextmanager
from dataclasses import dataclass
from time import monotonic
from typing import Any, AsyncIterator

from contratos.demo_settings import SettingsDemoConfig
from contratos.mcp import HarnessError, McpErrorCode
from logica.sesiones.appium import close_driver, create_device_driver


_SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{24,128}$")


@dataclass
class _ActiveUiFlow:
    session_id: str
    driver: Any
    expires_at: float


class UiFlowSessions:
    """Keep at most one explicit, short-lived Appium session at a time."""

    def __init__(self, idle_timeout_seconds: int, close_timeout_seconds: int) -> None:
        self._idle_timeout_seconds = idle_timeout_seconds
        self._close_timeout_seconds = close_timeout_seconds
        self._active: _ActiveUiFlow | None = None
        self._lock = asyncio.Lock()
        self._expiry_task: asyncio.Task[None] | None = None

    async def open(self, config: SettingsDemoConfig) -> str:
        """Open the sole flow driver and return an opaque capability identifier."""

        async with self._lock:
            await self._expire_locked()
            if self._active is not None:
                raise HarnessError(
                    McpErrorCode.EMULATOR_BUSY,
                    "A UI flow already owns the emulator. Close it or wait for it to expire.",
                )
            driver = await asyncio.to_thread(create_device_driver, config)
            session_id = secrets.token_urlsafe(24)
            self._active = _ActiveUiFlow(
                session_id=session_id,
                driver=driver,
                expires_at=monotonic() + self._idle_timeout_seconds,
            )
            self._schedule_expiry_locked()
            return session_id

    async def assert_idle(self) -> None:
        """Reject a competing UI mutation while an explicit flow owns the AVD."""

        async with self._lock:
            await self._expire_locked()
            if self._active is not None:
                raise HarnessError(
                    McpErrorCode.EMULATOR_BUSY,
                    "A UI flow owns the emulator; use its session_id or close the flow first.",
                )

    @asynccontextmanager
    async def use(self, raw_session_id: object) -> AsyncIterator[Any]:
        """Borrow the matching driver and renew its idle lease for one action."""

        session_id = self._validate_id(raw_session_id)
        async with self._lock:
            await self._expire_locked()
            if self._active is None or self._active.session_id != session_id:
                raise HarnessError(
                    McpErrorCode.INVALID_UI_SESSION,
                    "The UI session is unknown or has expired. Open a new UI session.",
                )
            self._active.expires_at = monotonic() + self._idle_timeout_seconds
            self._schedule_expiry_locked()
            try:
                yield self._active.driver
            except HarnessError as exc:
                # A command that ran out of time leaves the driver in an unknown
                # state with its worker thread still going. Handing that to the
                # next action would poison the chain, so the lease is voided:
                # the next call expires it on entry and the reaper closes it.
                # The controller has already turned the raw TimeoutError into a
                # typed one by the time it reaches here, so the code is what is
                # inspected, not the exception class.
                if (
                    exc.code is McpErrorCode.OPERATION_TIMEOUT
                    and self._active is not None
                    and self._active.session_id == session_id
                ):
                    self._active.expires_at = 0.0
                raise

    async def close(self, raw_session_id: object) -> None:
        """Close the matching flow immediately; a different client cannot close it."""

        session_id = self._validate_id(raw_session_id)
        async with self._lock:
            await self._expire_locked()
            if self._active is None or self._active.session_id != session_id:
                raise HarnessError(
                    McpErrorCode.INVALID_UI_SESSION,
                    "The UI session is unknown or has already expired.",
                )
            await self._close_locked()

    @staticmethod
    def _validate_id(raw_session_id: object) -> str:
        if not isinstance(raw_session_id, str) or not _SESSION_ID.fullmatch(raw_session_id):
            raise HarnessError(
                McpErrorCode.INVALID_UI_SESSION,
                "session_id must be the opaque identifier returned by ui.session.open.",
            )
        return raw_session_id

    def _schedule_expiry_locked(self) -> None:
        current = asyncio.current_task()
        if self._expiry_task is not None and self._expiry_task is not current:
            self._expiry_task.cancel()
        assert self._active is not None
        self._expiry_task = asyncio.create_task(
            self._expire_after(self._active.session_id, self._active.expires_at)
        )

    async def _expire_after(self, session_id: str, deadline: float) -> None:
        await asyncio.sleep(max(0.0, deadline - monotonic()))
        async with self._lock:
            if (
                self._active is not None
                and self._active.session_id == session_id
                and self._active.expires_at <= monotonic()
            ):
                await self._close_locked()

    async def _expire_locked(self) -> None:
        if self._active is not None and self._active.expires_at <= monotonic():
            await self._close_locked()

    async def _close_locked(self) -> None:
        assert self._active is not None
        driver = self._active.driver
        self._active = None
        current = asyncio.current_task()
        if self._expiry_task is not None and self._expiry_task is not current:
            self._expiry_task.cancel()
        self._expiry_task = None
        try:
            # Closing runs while this lock is held. A driver that will not quit
            # would otherwise keep the lease unreachable forever, so the wait is
            # bounded and the slot is freed either way.
            await asyncio.wait_for(
                asyncio.to_thread(close_driver, driver), self._close_timeout_seconds
            )
        except TimeoutError:
            pass
