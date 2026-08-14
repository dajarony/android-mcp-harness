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
from logica.evidencias.capturas import read_artifact_bytes
from logica.servicios.mcp_server.controller import AndroidMcpController


def build_server(controller: AndroidMcpController | None = None) -> MCPServer:
    """Create the local stdio MCP server with only its approved tools."""

    active_controller = controller or AndroidMcpController(
        SettingsDemoConfig(
            appium_url=os.getenv("APPIUM_URL", "http://127.0.0.1:4723"),
            udid=os.getenv("ANDROID_UDID", "emulator-5554"),
            connect_timeout_seconds=int(os.getenv("ANDROID_MCP_CONNECT_TIMEOUT", "120")),
            flow_idle_timeout_seconds=int(
                os.getenv("ANDROID_MCP_FLOW_IDLE_TIMEOUT", "60")
            ),
        )
    )
    server = MCPServer(
        name="Android Emulator Harness",
        version="0.8.0",
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
    async def ui_get_tree(include_raw: bool = False) -> dict[str, Any]:
        """List what the current Android screen says and what can be acted on.

        Every returned selector is one this server accepts for ui.tap and
        ui.type_text. Set include_raw to also receive the full XML dump.
        """

        return await active_controller.get_ui_tree(include_raw)

    @server.tool(name="screen.capture")
    async def screen_capture() -> dict[str, Any]:
        """Save one local screenshot without changing the visible Android screen."""

        return await active_controller.capture_screen()

    @server.tool(name="settings.open_apps")
    async def settings_open_apps() -> dict[str, Any]:
        """Open Android Settings and navigate to its Apps screen with evidence."""

        return await active_controller.open_settings_apps()

    @server.tool(name="ui.session.open")
    async def ui_session_open() -> dict[str, Any]:
        """Open a short-lived exclusive UI flow for chained semantic actions."""

        return await active_controller.open_ui_session()

    @server.tool(name="ui.session.close")
    async def ui_session_close(session_id: str) -> dict[str, Any]:
        """Close the UI flow identified by the opaque token from ui.session.open."""

        return await active_controller.close_ui_session(session_id)

    @server.tool(name="app.list_installed")
    async def app_list_installed() -> dict[str, Any]:
        """List package identifiers installed in the configured emulator only."""

        return await active_controller.list_installed_apps()

    @server.tool(name="app.open")
    async def app_open(package_name: str) -> dict[str, Any]:
        """Open one validated installed package in the disposable emulator."""

        return await active_controller.open_app(package_name)

    @server.tool(name="ui.tap")
    async def ui_tap(
        selector: dict[str, Any], session_id: str | None = None
    ) -> dict[str, Any]:
        """Tap one UI target selected by text, resource id or accessibility label."""

        return await active_controller.tap_ui(selector, session_id)

    @server.tool(name="ui.type_text")
    async def ui_type_text(
        selector: dict[str, Any], text: str, session_id: str | None = None
    ) -> dict[str, Any]:
        """Type bounded text into one semantic Android UI target."""

        return await active_controller.type_into_ui(selector, text, session_id)

    @server.tool(name="ui.scroll")
    async def ui_scroll(
        direction: str, session_id: str | None = None
    ) -> dict[str, Any]:
        """Scroll the current screen once using a trusted normalized gesture."""

        return await active_controller.scroll_ui(direction, session_id)

    @server.tool(name="device.back")
    async def device_back(session_id: str | None = None) -> dict[str, Any]:
        """Perform one Android Back navigation on the configured emulator."""

        return await active_controller.go_back(session_id)

    @server.resource(
        "artifact://{artifact_id}",
        name="Android evidence",
        description="One screenshot this harness recorded, by its artifact_id.",
        mime_type="image/png",
    )
    def read_evidence(artifact_id: str) -> bytes:
        """Serve recorded evidence so a client without the filesystem can see it."""

        return read_artifact_bytes(artifact_id)

    return server


mcp = build_server()


def main() -> None:
    """Run MCP on stdio only, as required for local agent integration."""

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
