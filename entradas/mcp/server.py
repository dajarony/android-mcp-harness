"""
SUME DOCBLOCK

Nombre: server
Tipo: Entrada

Entradas:
- Solicitudes MCP por stdio para herramientas Android declaradas.

Acciones:
- Registra el catálogo MCP y delega cada llamada al controlador autorizado.

Salidas:
- Respuestas MCP estructuradas; no abre ningún puerto de red.
"""

from __future__ import annotations

import os
from typing import Any

from mcp.server import MCPServer

from contratos.demo_settings import SettingsDemoConfig
from logica.servicios.mcp_server.controller import AndroidMcpController


def build_server(controller: AndroidMcpController | None = None) -> MCPServer:
    """Create the local stdio MCP server with only its approved tools."""

    active_controller = controller or AndroidMcpController(
        SettingsDemoConfig(
            appium_url=os.getenv("APPIUM_URL", "http://127.0.0.1:4723"),
            udid=os.getenv("ANDROID_UDID", "emulator-5554"),
        )
    )
    server = MCPServer(
        name="Android Emulator Harness",
        version="0.3.0",
        instructions=(
            "Controls only the configured disposable Android emulator. "
            "Use semantic UI tools and inspect returned evidence."
        ),
    )

    @server.tool(name="emulator.get_status")
    async def emulator_get_status() -> dict[str, Any]:
        """Read local emulator and Appium availability without changing Android UI."""

        return await active_controller.get_emulator_status()

    @server.tool(name="ui.get_tree")
    async def ui_get_tree() -> dict[str, Any]:
        """Read the current Android accessibility/UI tree without input events."""

        return await active_controller.get_ui_tree()

    @server.tool(name="screen.capture")
    async def screen_capture() -> dict[str, Any]:
        """Save one local screenshot without changing the visible Android screen."""

        return await active_controller.capture_screen()

    @server.tool(name="settings.open_apps")
    async def settings_open_apps() -> dict[str, Any]:
        """Open Android Settings and navigate to its Apps screen with evidence."""

        return await active_controller.open_settings_apps()

    @server.tool(name="app.list_installed")
    async def app_list_installed() -> dict[str, Any]:
        """List package identifiers installed in the configured emulator only."""

        return await active_controller.list_installed_apps()

    @server.tool(name="app.open")
    async def app_open(package_name: str) -> dict[str, Any]:
        """Open one validated installed package in the disposable emulator."""

        return await active_controller.open_app(package_name)

    @server.tool(name="ui.tap")
    async def ui_tap(selector: dict[str, str]) -> dict[str, Any]:
        """Tap one UI target selected by text, resource id or accessibility label."""

        return await active_controller.tap_ui(selector)

    @server.tool(name="ui.type_text")
    async def ui_type_text(selector: dict[str, str], text: str) -> dict[str, Any]:
        """Type bounded text into one semantic Android UI target."""

        return await active_controller.type_into_ui(selector, text)

    @server.tool(name="ui.scroll")
    async def ui_scroll(direction: str) -> dict[str, Any]:
        """Scroll the current screen once using a trusted normalized gesture."""

        return await active_controller.scroll_ui(direction)

    @server.tool(name="device.back")
    async def device_back() -> dict[str, Any]:
        """Perform one Android Back navigation on the configured emulator."""

        return await active_controller.go_back()

    return server


mcp = build_server()


def main() -> None:
    """Run MCP on stdio only, as required for local agent integration."""

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
