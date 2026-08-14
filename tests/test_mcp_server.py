"""Protocol-level tests for the official in-memory MCP server client."""

import unittest

from mcp.client import Client

from entradas.mcp.server import build_server


class FakeMcpController:
    """No-emulator double proving that entry code delegates to controller methods."""

    async def get_emulator_status(self) -> dict[str, object]:
        return {"ok": True, "tool": "emulator.get_status"}

    async def get_ui_tree(
        self, include_raw: object = False, session_id: object = None
    ) -> dict[str, object]:
        return {
            "ok": True,
            "tool": "ui.get_tree",
            "include_raw": include_raw,
            "session_id": session_id,
        }

    async def capture_screen(self) -> dict[str, object]:
        return {"ok": True, "tool": "screen.capture"}

    async def open_settings_apps(self) -> dict[str, object]:
        return {"ok": True, "tool": "settings.open_apps"}

    async def open_ui_session(self) -> dict[str, object]:
        return {"ok": True, "tool": "ui.session.open"}

    async def close_ui_session(self, session_id: object) -> dict[str, object]:
        return {"ok": True, "tool": "ui.session.close", "session_id": session_id}

    async def list_installed_apps(self) -> dict[str, object]:
        return {"ok": True, "tool": "app.list_installed"}

    async def open_app(self, package_name: object) -> dict[str, object]:
        return {"ok": True, "tool": "app.open", "package_name": package_name}

    async def tap_ui(self, selector: object, session_id: object = None) -> dict[str, object]:
        return {"ok": True, "tool": "ui.tap", "selector": selector}

    async def type_into_ui(
        self, selector: object, text: object, session_id: object = None
    ) -> dict[str, object]:
        return {"ok": True, "tool": "ui.type_text", "selector": selector, "text": text}

    async def scroll_ui(self, direction: object, session_id: object = None) -> dict[str, object]:
        return {"ok": True, "tool": "ui.scroll", "direction": direction}

    async def go_back(self, session_id: object = None) -> dict[str, object]:
        return {"ok": True, "tool": "device.back"}


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
                "ui.session.open",
                "ui.session.close",
                "app.list_installed",
                "app.open",
                "ui.tap",
                "ui.type_text",
                "ui.scroll",
                "device.back",
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

    async def test_tree_can_read_the_owned_flow_snapshot(self) -> None:
        """A flow token lets observation stay on the same Appium session."""

        async with Client(build_server(FakeMcpController())) as client:
            result = await client.call_tool(
                "ui.get_tree", {"session_id": "flow-opaque-token"}
            )

        self.assertFalse(result.is_error)
        self.assertEqual(
            result.structured_content,
            {
                "ok": True,
                "tool": "ui.get_tree",
                "include_raw": False,
                "session_id": "flow-opaque-token",
            },
        )

    async def test_action_arguments_reach_only_the_matching_controller_method(self) -> None:
        """The MCP entry delegates action input rather than interpreting it itself."""

        async with Client(build_server(FakeMcpController())) as client:
            result = await client.call_tool(
                "ui.tap",
                {
                    "selector": {
                        "text": "Save",
                        "within": {"content_desc": "Personal profile"},
                    }
                },
            )

        self.assertFalse(result.is_error)
        self.assertEqual(
            result.structured_content,
            {
                "ok": True,
                "tool": "ui.tap",
                "selector": {
                    "text": "Save",
                    "within": {"content_desc": "Personal profile"},
                },
            },
        )
