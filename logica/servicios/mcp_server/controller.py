"""
SUME DOCBLOCK

Nombre: controller
Tipo: Lógica

Entradas:
- SettingsDemoConfig y llamadas de herramientas MCP sin parámetros.

Acciones:
- Coordina adaptadores de lectura, navegación y evidencia bajo un bloqueo único.

Salidas:
- McpToolResult normalizado para cada herramienta declarada.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from contratos.demo_settings import SettingsDemoConfig
from contratos.mcp import HarnessError, McpErrorCode, McpToolResult
from logica.controladores.demo_settings import run_settings_demo
from logica.evidencias.capturas import ARTIFACTS, save_png_artifact
from logica.infraestructura.adb import (
    read_emulator_properties,
    read_png_screenshot,
    read_ui_tree,
)
from logica.infraestructura.appium import read_appium_status
from logica.seguridad.emulador import assert_emulator_udid
from logica.servicios.mcp_server.gate import EmulatorOperationGate


ToolAction = Callable[[], Awaitable[tuple[dict[str, Any], dict[str, str] | None]]]


class AndroidMcpController:
    """Coordinate the explicitly permitted Android MCP tool actions."""

    def __init__(
        self,
        config: SettingsDemoConfig,
        gate: EmulatorOperationGate | None = None,
    ) -> None:
        self._config = config
        self._gate = gate or EmulatorOperationGate()

    async def get_emulator_status(self) -> dict[str, Any]:
        """Return read-only ADB and Appium status data."""

        return (await self._execute("emulator.get_status", self._read_status)).to_dict()

    async def get_ui_tree(self) -> dict[str, Any]:
        """Return a read-only Android UI hierarchy."""

        return (await self._execute("ui.get_tree", self._read_tree)).to_dict()

    async def capture_screen(self) -> dict[str, Any]:
        """Capture the current Android screen without UI input."""

        return (await self._execute("screen.capture", self._capture_screen)).to_dict()

    async def open_settings_apps(self) -> dict[str, Any]:
        """Navigate Settings to Apps under the single-operation gate."""

        return (await self._execute("settings.open_apps", self._open_settings_apps)).to_dict()

    async def _execute(self, tool: str, action: ToolAction) -> McpToolResult:
        """Apply concurrency and typed-error policy around one declared tool."""

        try:
            async with self._gate.acquire():
                data, evidence = await action()
                return McpToolResult.success(tool, data, evidence)
        except HarnessError as exc:
            return McpToolResult.failure(tool, exc)
        except Exception:
            return McpToolResult.failure(
                tool,
                HarnessError(
                    McpErrorCode.INTERNAL_ERROR,
                    "The emulator tool failed unexpectedly; inspect local evidence and logs.",
                ),
            )

    async def _read_status(self) -> tuple[dict[str, Any], None]:
        """Gather fixed status fields from local read-only adapters."""

        assert_emulator_udid(self._config.udid)
        device, appium = await asyncio.gather(
            asyncio.to_thread(read_emulator_properties, self._config.udid),
            asyncio.to_thread(read_appium_status, self._config.appium_url),
        )
        return {**device, **appium}, None

    async def _read_tree(self) -> tuple[dict[str, Any], None]:
        """Read the current UI XML through the fixed ADB adapter."""

        tree = await asyncio.to_thread(read_ui_tree, self._config.udid)
        return {"ui_tree": tree}, None

    async def _capture_screen(self) -> tuple[dict[str, Any], dict[str, str]]:
        """Persist a read-only ADB screenshot and expose a safe artifact reference."""

        payload = await asyncio.to_thread(read_png_screenshot, self._config.udid)
        path = await asyncio.to_thread(save_png_artifact, payload, "screen")
        return {"captured": True}, self._artifact_reference(path)

    async def _open_settings_apps(self) -> tuple[dict[str, Any], dict[str, str] | None]:
        """Run the already-proven Appium Settings flow in a worker thread."""

        result = await asyncio.to_thread(run_settings_demo, self._config)
        evidence = self._artifact_reference(Path(result.screenshot_path)) if result.screenshot_path else None
        if not result.succeeded:
            code = McpErrorCode(result.error_code or McpErrorCode.INTERNAL_ERROR)
            raise HarnessError(code, result.detail)
        return {"screen_marker": result.detail}, evidence

    @staticmethod
    def _artifact_reference(path: Path) -> dict[str, str]:
        """Convert an absolute evidence path into an MCP-safe relative reference."""

        try:
            relative = path.resolve().relative_to(ARTIFACTS.resolve())
        except ValueError as exc:
            raise HarnessError(
                McpErrorCode.EVIDENCE_WRITE_FAILED,
                "Evidence was produced outside the permitted artifacts directory.",
            ) from exc
        return {"artifact_id": path.name, "path": f"artifacts/{relative.as_posix()}"}
