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
from logica.evidencias.capturas import ARTIFACTS, save_png_artifact, save_screenshot
from logica.infraestructura.adb import (
    read_emulator_properties,
    read_installed_packages,
    read_png_screenshot,
    read_ui_tree,
)
from logica.infraestructura.appium import read_appium_status
from logica.infraestructura.lanzador import launch_package
from logica.navegacion.semantica import (
    go_back,
    scroll,
    tap,
    type_text,
)
from logica.seguridad.emulador import assert_emulator_udid
from logica.servicios.mcp_server.gate import EmulatorOperationGate
from logica.sesiones.appium import close_driver, create_device_driver
from contratos.ui_control import (
    selector_mapping,
    validate_package_name,
    validate_scroll_direction,
    validate_selector,
    validate_text,
)


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

    async def list_installed_apps(self) -> dict[str, Any]:
        """List installed package identifiers through the fixed ADB read adapter."""

        return (await self._execute("app.list_installed", self._list_installed_apps)).to_dict()

    async def open_app(self, package_name: object) -> dict[str, Any]:
        """Activate one validated Android package and capture the result."""

        return (
            await self._execute(
                "app.open", lambda: self._open_app(package_name)
            )
        ).to_dict()

    async def tap_ui(self, selector: object) -> dict[str, Any]:
        """Tap one semantic UI target and capture the result."""

        return (
            await self._execute("ui.tap", lambda: self._tap_ui(selector))
        ).to_dict()

    async def type_into_ui(self, selector: object, text: object) -> dict[str, Any]:
        """Send validated text into one semantic UI target and capture the result."""

        return (
            await self._execute(
                "ui.type_text", lambda: self._type_into_ui(selector, text)
            )
        ).to_dict()

    async def scroll_ui(self, direction: object) -> dict[str, Any]:
        """Perform one normalized semantic scroll and capture the result."""

        return (
            await self._execute("ui.scroll", lambda: self._scroll_ui(direction))
        ).to_dict()

    async def go_back(self) -> dict[str, Any]:
        """Navigate Android Back once and capture the result."""

        return (await self._execute("device.back", self._go_back)).to_dict()

    async def _execute(self, tool: str, action: ToolAction) -> McpToolResult:
        """Apply concurrency and typed-error policy around one declared tool."""

        try:
            async with self._gate.acquire():
                data, evidence = await action()
                return McpToolResult.success(tool, data, evidence)
        except HarnessError as exc:
            return McpToolResult.failure(tool, exc, exc.evidence)
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

    async def _list_installed_apps(self) -> tuple[dict[str, Any], None]:
        """Read available package identifiers without creating an Appium session."""

        packages = await asyncio.to_thread(read_installed_packages, self._config.udid)
        return {"packages": packages, "count": len(packages)}, None

    async def _open_app(
        self, package_name: object
    ) -> tuple[dict[str, Any], dict[str, str] | None]:
        """Validate then activate one app through the transient Appium session."""

        package = validate_package_name(package_name)
        launched = await asyncio.to_thread(launch_package, self._config.udid, package)
        await self._await_visible_package(launched)
        screenshot = await asyncio.to_thread(read_png_screenshot, self._config.udid)
        path = await asyncio.to_thread(save_png_artifact, screenshot, "app-open")
        return (
            {"opened_package": launched, "foreground_package": launched},
            self._artifact_reference(path),
        )

    async def _await_visible_package(
        self, package: str, deadline_seconds: float = 6.0
    ) -> None:
        """Give Android time to draw before declaring the app missing.

        The previous check read the tree once and still reported a timeout, so a
        launch that was merely mid-animation looked like a missing app.  A dump
        taken during a transition can also fail outright; that is a reason to
        retry, not to give up.
        """

        loop = asyncio.get_running_loop()
        deadline = loop.time() + deadline_seconds
        while True:
            try:
                tree = await asyncio.to_thread(read_ui_tree, self._config.udid)
                if f'package="{package}"' in tree:
                    return
            except HarnessError:
                pass
            if loop.time() >= deadline:
                raise HarnessError(
                    McpErrorCode.APP_NOT_FOUND,
                    "Android launched the package but it did not become visible "
                    f"within {deadline_seconds:.0f} s.",
                )
            await asyncio.sleep(0.5)

    async def _tap_ui(
        self, raw_selector: object
    ) -> tuple[dict[str, Any], dict[str, str] | None]:
        """Validate then tap the one requested semantic target."""

        selector = validate_selector(raw_selector)
        return await self._run_ui_action(
            "ui-tap",
            lambda driver: {
                "target": selector_mapping(selector),
                "element_label": tap(driver, selector),
            },
        )

    async def _type_into_ui(
        self, raw_selector: object, raw_text: object
    ) -> tuple[dict[str, Any], dict[str, str] | None]:
        """Validate then send text into the requested semantic target."""

        selector = validate_selector(raw_selector)
        text = validate_text(raw_text)
        return await self._run_ui_action(
            "ui-type",
            lambda driver: {
                "target": selector_mapping(selector),
                "characters_sent": type_text(driver, selector, text),
            },
        )

    async def _scroll_ui(
        self, raw_direction: object
    ) -> tuple[dict[str, Any], dict[str, str] | None]:
        """Validate direction then execute one trusted normalized scroll."""

        direction = validate_scroll_direction(raw_direction)
        return await self._run_ui_action(
            "ui-scroll",
            lambda driver: self._scroll_action(driver, direction),
        )

    async def _go_back(self) -> tuple[dict[str, Any], dict[str, str] | None]:
        """Run one Back action through a transient Appium session."""

        return await self._run_ui_action(
            "device-back", lambda driver: {"back_to_package": go_back(driver)}
        )

    async def _run_ui_action(
        self,
        evidence_label: str,
        action: Callable[[Any], dict[str, Any]],
    ) -> tuple[dict[str, Any], dict[str, str] | None]:
        """Own the session lifecycle and evidence policy for a single UI action."""

        driver: Any | None = None
        try:
            driver = await asyncio.to_thread(create_device_driver, self._config)
            data = await asyncio.to_thread(action, driver)
            data["foreground_package"] = str(driver.current_package)
            screenshot = await asyncio.to_thread(save_screenshot, driver, evidence_label)
            return data, self._artifact_reference(screenshot)
        except HarnessError as exc:
            raise self._with_failure_evidence(exc, driver, evidence_label) from exc
        except Exception as exc:
            error = HarnessError(
                McpErrorCode.INTERNAL_ERROR,
                "The Android UI action failed unexpectedly; inspect local evidence and logs.",
            )
            raise self._with_failure_evidence(error, driver, evidence_label) from exc
        finally:
            if driver is not None:
                await asyncio.to_thread(close_driver, driver)

    @staticmethod
    def _scroll_action(driver: Any, direction: str) -> dict[str, Any]:
        """Run one scroll and expose the declared direction only."""

        scroll(driver, direction)
        return {"direction": direction}

    def _with_failure_evidence(
        self,
        error: HarnessError,
        driver: Any | None,
        label: str,
    ) -> HarnessError:
        """Attach a best-effort local screenshot without hiding the original cause."""

        if driver is None:
            return error
        try:
            screenshot = save_screenshot(driver, f"failure-{label}")
            return HarnessError(error.code, error.message, self._artifact_reference(screenshot))
        except Exception:
            return error

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
