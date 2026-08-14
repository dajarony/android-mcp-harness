"""
SUME DOCBLOCK

Nombre: ejecutor_ui
Tipo: Lógica

Entradas:
- Una acción semántica ya validada, un driver Appium temporal o de flujo y su etiqueta de evidencia.

Acciones:
- Ejecuta las llamadas al driver bajo un techo, conserva la evidencia y cierra drivers temporales.

Salidas:
- Datos de la acción con evidencia, o HarnessError tipado sin bloquear el emulador.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from contratos.demo_settings import SettingsDemoConfig
from contratos.mcp import HarnessError, McpErrorCode
from logica.evidencias.capturas import save_screenshot
from logica.sesiones.flujo import UiFlowSessions


DriverAction = Callable[[Any], dict[str, Any]]
DriverFactory = Callable[[SettingsDemoConfig], Any]
DriverCloser = Callable[[Any], None]
EvidenceReference = Callable[[Any], dict[str, str]]


class UiActionExecutor:
    """Own driver lifecycle, deadlines and proof for one semantic UI action."""

    def __init__(
        self,
        config: SettingsDemoConfig,
        flows: UiFlowSessions,
        create_driver: DriverFactory,
        close_driver: DriverCloser,
        artifact_reference: EvidenceReference,
    ) -> None:
        self._config = config
        self._flows = flows
        self._create_driver = create_driver
        self._close_driver = close_driver
        self._artifact_reference = artifact_reference

    async def run(
        self,
        evidence_label: str,
        action: DriverAction,
        session_id: object = None,
    ) -> tuple[dict[str, Any], dict[str, str] | None]:
        """Run one action with either a flow-owned or temporary driver."""

        if session_id is not None:
            async with self._flows.use(session_id) as driver:
                return await self._run_driver_action(driver, evidence_label, action)

        await self._flows.assert_idle()
        driver: Any | None = None
        try:
            driver = await asyncio.to_thread(self._create_driver, self._config)
            return await self._run_driver_action(driver, evidence_label, action)
        finally:
            if driver is not None:
                await self.before_ceiling(
                    asyncio.to_thread(self._close_driver, driver)
                )

    async def flow_page_source(self, session_id: object) -> str:
        """Read an owned flow snapshot without allowing a driver call to freeze MCP."""

        async with self._flows.use(session_id) as driver:
            return await self.before_ceiling(
                asyncio.to_thread(lambda: str(driver.page_source))
            )

    async def before_ceiling(self, work: Awaitable[Any]) -> Any:
        """Stop waiting when a driver call no longer answers.

        A worker thread cannot be killed. It may therefore finish later against a
        driver nobody reads, but the waiting coroutine unwinds so the gate and
        any poisoned flow lease can be released.
        """

        return await asyncio.wait_for(work, self._config.action_timeout_seconds)

    async def _run_driver_action(
        self,
        driver: Any,
        evidence_label: str,
        action: DriverAction,
    ) -> tuple[dict[str, Any], dict[str, str] | None]:
        """Execute and prove an action against an already-owned driver."""

        try:
            data = await self.before_ceiling(asyncio.to_thread(action, driver))
            data["foreground_package"] = await self.before_ceiling(
                asyncio.to_thread(lambda: str(driver.current_package))
            )
            screenshot = await self.before_ceiling(
                asyncio.to_thread(save_screenshot, driver, evidence_label)
            )
            return data, self._artifact_reference(screenshot)
        except TimeoutError as exc:
            raise HarnessError(
                McpErrorCode.OPERATION_TIMEOUT,
                "The Android UI action did not finish within "
                f"{self._config.action_timeout_seconds} s and was abandoned so the "
                "emulator stays usable. Raise ANDROID_MCP_ACTION_TIMEOUT if the "
                "device is simply slow.",
            ) from exc
        except HarnessError as exc:
            raise await self._with_failure_evidence(exc, driver, evidence_label) from exc
        except Exception as exc:
            error = HarnessError(
                McpErrorCode.INTERNAL_ERROR,
                "The Android UI action failed unexpectedly; inspect local evidence and logs.",
            )
            raise await self._with_failure_evidence(error, driver, evidence_label) from exc

    async def _with_failure_evidence(
        self,
        error: HarnessError,
        driver: Any | None,
        label: str,
    ) -> HarnessError:
        """Attach bounded best-effort evidence without hiding the original failure."""

        if driver is None:
            return error
        try:
            screenshot = await self.before_ceiling(
                asyncio.to_thread(save_screenshot, driver, f"failure-{label}")
            )
            return HarnessError(error.code, error.message, self._artifact_reference(screenshot))
        except Exception:
            return error
