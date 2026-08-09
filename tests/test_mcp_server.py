"""Protocol-level tests for the official in-memory MCP server client."""

import unittest

from mcp.client import Client

from entradas.mcp.server import build_server


class FakeMcpController:
    """No-emulator double proving that entry code delegates to controller methods."""

    async def get_emulator_status(self) -> dict[str, object]:
        return {"ok": True, "tool": "emulator.get_status"}

    async def get_ui_tree(self) -> dict[str, object]:
        return {"ok": True, "tool": "ui.get_tree"}

    async def capture_screen(self) -> dict[str, object]:
        return {"ok": True, "tool": "screen.capture"}

    async def open_settings_apps(self) -> dict[str, object]:
        return {"ok": True, "tool": "settings.open_apps"}


class McpServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_catalog_exposes_only_declared_custom_tools(self) -> None:
        async with Client(build_server(FakeMcpController())) as client:
            tools = await client.list_tools()

        self.assertEqual(
            {tool.name for tool in tools.tools},
            {
                "emulator.get_status",
                "ui.get_tree",
                "screen.capture",
                "settings.open_apps",
            },
        )

    async def test_tool_delegates_to_controller_through_mcp(self) -> None:
        async with Client(build_server(FakeMcpController())) as client:
            result = await client.call_tool("emulator.get_status")

        self.assertFalse(result.is_error)
        self.assertEqual(
            result.structured_content,
            {"ok": True, "tool": "emulator.get_status"},
        )
