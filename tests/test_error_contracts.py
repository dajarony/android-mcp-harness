"""Regressions for the promises an MCP client relies on when things go wrong.

Every case here was found by running an agent against the live harness, not by
reading the code: the previous suite passed while each of these was broken.
"""

import socket
import unittest
from unittest.mock import patch

from contratos.demo_settings import SettingsDemoConfig
from contratos.mcp import HarnessError, McpErrorCode
from contratos.ui_control import validate_package_name, validate_selector, validate_text
from logica.evidencias.capturas import ARTIFACTS
from logica.controladores.demo_settings import run_settings_demo
from logica.servicios.mcp_server.controller import AndroidMcpController


def _closed_loopback_port() -> int:
    """Reserve then release a port so nothing answers on it during the test."""

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


DEAD_APPIUM = f"http://127.0.0.1:{_closed_loopback_port()}"
LEAKY_MESSAGE = r"connection to http://10.0.0.5:4723/session from C:\Users\secret failed"


def controller(appium_url: str = DEAD_APPIUM) -> AndroidMcpController:
    return AndroidMcpController(
        SettingsDemoConfig(appium_url=appium_url, udid="emulator-5554")
    )


class PublicErrorMessageTests(unittest.TestCase):
    """The FASER promises no stacktrace and no path outside artifacts/."""

    def test_navigation_failure_never_repeats_the_raw_exception(self) -> None:
        with patch(
            "logica.controladores.demo_settings.create_settings_driver",
            side_effect=RuntimeError(LEAKY_MESSAGE),
        ):
            result = run_settings_demo(
                SettingsDemoConfig(appium_url=DEAD_APPIUM, udid="emulator-5554")
            )

        self.assertFalse(result.succeeded)
        for leak in ("http://", "/session", "C:\\", "RuntimeError", "10.0.0.5"):
            self.assertNotIn(leak, result.detail, f"public detail leaked {leak!r}")

    def test_guard_failures_keep_their_typed_code_and_own_wording(self) -> None:
        with patch(
            "logica.controladores.demo_settings.create_settings_driver",
            side_effect=HarnessError(
                McpErrorCode.EMULATOR_UNAVAILABLE,
                "Configured ANDROID_UDID is not an Android emulator identifier.",
            ),
        ):
            result = run_settings_demo(
                SettingsDemoConfig(appium_url=DEAD_APPIUM, udid="emulator-5554")
            )

        self.assertEqual(result.error_code, "EMULATOR_UNAVAILABLE")


class AppiumAvailabilityTests(unittest.IsolatedAsyncioTestCase):
    """A stopped Appium is a declared, recoverable condition, not a surprise."""

    async def test_every_action_tool_reports_appium_unavailable(self) -> None:
        active = controller()
        results = {
            "ui.tap": await active.tap_ui({"text": "Apps"}),
            "ui.type_text": await active.type_into_ui({"text": "Apps"}, "hola"),
            "ui.scroll": await active.scroll_ui("down"),
            "device.back": await active.go_back(),
            "settings.open_apps": await active.open_settings_apps(),
        }

        for tool, result in results.items():
            self.assertEqual(result["error"]["code"], "APPIUM_UNAVAILABLE", tool)


class ControlCharacterTests(unittest.TestCase):
    """A newline in an Android field is an IME action, not typed text."""

    def test_text_rejects_control_characters_and_bidi_overrides(self) -> None:
        for hostile in ("hola\n", "hola\r", "hola\ttab", "hola\x1b", "hola\u202e", "hola\x7f"):
            with self.subTest(text=repr(hostile)), self.assertRaises(HarnessError) as raised:
                validate_text(hostile)
            self.assertEqual(raised.exception.code.value, "INVALID_TEXT")

    def test_selector_rejects_control_characters_and_bidi_overrides(self) -> None:
        for hostile in ("Apps\n", "Apps\r", "Apps\x1b", "Apps\u202e"):
            with self.subTest(value=repr(hostile)), self.assertRaises(HarnessError) as raised:
                validate_selector({"text": hostile})
            self.assertEqual(raised.exception.code.value, "INVALID_SELECTOR")

    def test_ordinary_text_still_passes(self) -> None:
        self.assertEqual(validate_text("Buscar ajustes 123"), "Buscar ajustes 123")
        self.assertEqual(validate_selector({"text": "All apps"}).value, "All apps")


class PackageSyntaxTests(unittest.TestCase):
    """The server must accept the packages the server itself lists."""

    def test_single_segment_package_is_valid_android_syntax(self) -> None:
        self.assertEqual(validate_package_name("android"), "android")

    def test_shell_and_path_shapes_are_still_refused(self) -> None:
        for hostile in ("com.x; rm -rf /", "com.x/../../etc", "-e", "--user 0",
                        "com.x && whoami", "com.x\ncom.y", "com.android.settings/.Settings"):
            with self.subTest(package=hostile), self.assertRaises(HarnessError) as raised:
                validate_package_name(hostile)
            self.assertEqual(raised.exception.code.value, "INVALID_PACKAGE")


class AppVisibilityTests(unittest.IsolatedAsyncioTestCase):
    """app.open promised a timeout it never had; now it must actually wait."""

    async def test_open_app_retries_until_the_package_becomes_visible(self) -> None:
        trees = ['<hierarchy><node package="com.android.launcher"/></hierarchy>',
                 '<hierarchy><node package="com.android.launcher"/></hierarchy>',
                 '<hierarchy><node package="com.example.app"/></hierarchy>']
        calls = iter(trees)

        with patch("logica.servicios.mcp_server.controller.launch_package",
                   return_value="com.example.app"), \
             patch("logica.servicios.mcp_server.controller.read_ui_tree",
                   side_effect=lambda _udid: next(calls)), \
             patch("logica.servicios.mcp_server.controller.read_png_screenshot",
                   return_value=b"\x89PNG\r\n\x1a\n"), \
             patch("logica.servicios.mcp_server.controller.save_png_artifact",
                   side_effect=lambda payload, label: ARTIFACTS / "fake.png"):
            result = await controller().open_app("com.example.app")

        self.assertTrue(result["ok"], result.get("error"))
        self.assertEqual(result["data"]["foreground_package"], "com.example.app")

    async def test_open_app_gives_up_with_app_not_found(self) -> None:
        never = '<hierarchy><node package="com.android.launcher"/></hierarchy>'

        with patch("logica.servicios.mcp_server.controller.launch_package",
                   return_value="com.example.app"), \
             patch("logica.servicios.mcp_server.controller.read_ui_tree",
                   return_value=never):
            result = await controller().open_app("com.example.app")

        self.assertEqual(result["error"]["code"], "APP_NOT_FOUND")
