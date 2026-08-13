"""Regressions proving the emulator guards cover every session-opening tool.

An Appium spy replaces the real server: if any tool reaches it, the guard did not
run.  These cases exist because the earlier suite only checked one read-only tool.
"""

import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from contratos.demo_settings import SettingsDemoConfig
from logica.servicios.mcp_server.controller import AndroidMcpController


PHYSICAL_UDID = "R3CN90ABCDE"
REMOTE_APPIUM = "https://appium.example.invalid:4723"


class _AppiumSpy(BaseHTTPRequestHandler):
    """Record every request instead of behaving like Appium."""

    requests: list[str] = []

    def _record(self, method: str) -> None:
        _AppiumSpy.requests.append(f"{method} {self.path}")
        self.send_response(500)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"value": {"error": "unknown error"}}')

    def do_GET(self) -> None:  # noqa: N802
        self._record("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._record("POST")

    def log_message(self, *args: object) -> None:
        return


class SessionGuardTests(unittest.IsolatedAsyncioTestCase):
    """INV-SAFE-1: no tool may open a session outside the disposable emulator."""

    def setUp(self) -> None:
        _AppiumSpy.requests = []
        self._server = HTTPServer(("127.0.0.1", 0), _AppiumSpy)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        self.spy_url = f"http://127.0.0.1:{self._server.server_address[1]}"

    def tearDown(self) -> None:
        self._server.shutdown()
        self._server.server_close()

    def _controller(self, udid: str, appium_url: str) -> AndroidMcpController:
        return AndroidMcpController(SettingsDemoConfig(appium_url=appium_url, udid=udid))

    async def _every_action(self, controller: AndroidMcpController) -> dict[str, str]:
        """Call every tool that can open an Appium session."""

        results = {
            "ui.tap": await controller.tap_ui({"text": "Apps"}),
            "ui.type_text": await controller.type_into_ui({"text": "Apps"}, "hola"),
            "ui.scroll": await controller.scroll_ui("down"),
            "device.back": await controller.go_back(),
            "settings.open_apps": await controller.open_settings_apps(),
        }
        return {tool: result["error"]["code"] for tool, result in results.items()}

    async def test_physical_udid_never_reaches_appium(self) -> None:
        """A phone-shaped UDID is refused before the session request leaves."""

        codes = await self._every_action(self._controller(PHYSICAL_UDID, self.spy_url))

        self.assertEqual(_AppiumSpy.requests, [], "the guard let a session request out")
        for tool, code in codes.items():
            self.assertEqual(code, "EMULATOR_UNAVAILABLE", tool)

    async def test_non_loopback_appium_is_refused_before_connecting(self) -> None:
        """A remote Appium endpoint is refused by the same guard, not by the network."""

        codes = await self._every_action(self._controller("emulator-5554", REMOTE_APPIUM))

        for tool, code in codes.items():
            self.assertEqual(code, "APPIUM_UNAVAILABLE", tool)
