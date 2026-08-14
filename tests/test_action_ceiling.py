"""Regressions proving a hung driver call cannot freeze the whole harness.

A flow session holds the emulator lock for the length of an action. Without a
ceiling, one Appium command that never answers keeps that lock forever: the
idle timeout cannot fire, ui.session.close cannot run, and every client is
stuck until the process is restarted.
"""

import asyncio
import unittest
from unittest.mock import patch

from contratos.demo_settings import SettingsDemoConfig
from logica.servicios.mcp_server.controller import AndroidMcpController


CONFIG = SettingsDemoConfig(
    "http://127.0.0.1:4723", "emulator-5554", action_timeout_seconds=1
)


class _HungDriver:
    """A driver whose every call outlives the ceiling."""

    current_package = "com.example.app"

    def find_element(self, *_args: object) -> object:
        return self

    def get_attribute(self, _name: str) -> str:
        return "Apps"

    def click(self) -> None:
        import time

        # Comfortably past the one second ceiling these tests configure, and
        # short enough that the abandoned worker threads do not slow the bank.
        time.sleep(3)

    def save_screenshot(self, _path: str) -> None:
        return None

    def quit(self) -> None:
        return None


class ActionCeilingTests(unittest.IsolatedAsyncioTestCase):
    def _controller(self) -> AndroidMcpController:
        return AndroidMcpController(CONFIG)

    async def test_a_hung_action_answers_operation_timeout(self) -> None:
        with patch(
            "logica.servicios.mcp_server.controller.create_device_driver",
            return_value=_HungDriver(),
        ), patch("logica.servicios.mcp_server.controller.close_driver"):
            result = await self._controller().tap_ui({"text": "Apps"})

        self.assertEqual(result["error"]["code"], "OPERATION_TIMEOUT")
        self.assertIn("ANDROID_MCP_ACTION_TIMEOUT", result["error"]["message"])

    async def test_the_ceiling_is_honoured_rather_than_waited_out(self) -> None:
        """The point is not the code: it is that the caller gets it back quickly."""

        with patch(
            "logica.servicios.mcp_server.controller.create_device_driver",
            return_value=_HungDriver(),
        ), patch("logica.servicios.mcp_server.controller.close_driver"):
            started = asyncio.get_running_loop().time()
            await self._controller().tap_ui({"text": "Apps"})
            elapsed = asyncio.get_running_loop().time() - started

        self.assertLess(elapsed, 10, "the harness waited for the hung call")

    async def test_the_emulator_is_usable_again_afterwards(self) -> None:
        """A frozen action must not leave the gate or the flow lease held."""

        controller = self._controller()
        with patch(
            "logica.servicios.mcp_server.controller.create_device_driver",
            return_value=_HungDriver(),
        ), patch("logica.servicios.mcp_server.controller.close_driver"):
            await controller.tap_ui({"text": "Apps"})
            second = await controller.scroll_ui("sideways")

        # Reaching validation at all proves the gate was released.
        self.assertEqual(second["error"]["code"], "INVALID_SCROLL_DIRECTION")

    async def test_a_hung_flow_action_voids_its_lease(self) -> None:
        """The chain must not hand the next action a driver that stopped answering."""

        controller = self._controller()
        with patch(
            "logica.sesiones.flujo.create_device_driver", return_value=_HungDriver()
        ), patch("logica.sesiones.flujo.close_driver"), patch(
            "logica.servicios.mcp_server.controller.close_driver"
        ):
            opened = await controller.open_ui_session()
            session_id = opened["data"]["session_id"]
            hung = await controller.tap_ui({"text": "Apps"}, session_id)
            reused = await controller.tap_ui({"text": "Apps"}, session_id)

        self.assertEqual(hung["error"]["code"], "OPERATION_TIMEOUT")
        self.assertEqual(reused["error"]["code"], "INVALID_UI_SESSION")
