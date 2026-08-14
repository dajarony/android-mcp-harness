"""ECA campaign against the disposable Android emulator and real MCP transports.

This suite is opt-in because it requires the local Android SDK, an online AVD and
an Appium server.  It never accepts a physical-device UDID and only navigates the
emulator through the declared Settings flow.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import subprocess
import urllib.request
import unittest
import xml.etree.ElementTree as element_tree
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client import Client
from mcp.client.stdio import stdio_client

from contratos.demo_settings import SettingsDemoConfig
from contratos.ui_control import validate_selector
from entradas.mcp.server import build_server
from logica.navegacion.semantica import find_element
from logica.infraestructura.adb import resolve_adb_path
from logica.sesiones.appium import close_driver, create_device_driver


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_EMULATOR_ECA = os.getenv("ANDROID_MCP_RUN_EMULATOR") == "1"
TARGET_APP_PACKAGE = os.getenv("ANDROID_MCP_ECA_TARGET_PACKAGE")
# Appium keeps session listing behind --allow-insecure=session_discovery, so this
# check is opt-in rather than silently skipped: an unmeasured promise is not a
# kept one, and pretending otherwise is worse than saying it was never run.
CHECK_SESSIONS = os.getenv("ANDROID_MCP_CHECK_SESSIONS") == "1"


def open_appium_sessions() -> int:
    """Count sessions Appium still owns, or fail loudly if it will not say."""

    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:4723/appium/sessions", timeout=5
        ) as answer:
            payload = json.load(answer)
    except urllib.error.HTTPError as refused:
        # Answering with a bare HTTP 500 leaves the reader guessing at exactly
        # the moment the check is meant to be explicit about what it needs.
        raise AssertionError(
            "Appium will not list its sessions. Start it with "
            "--allow-insecure='*:session_discovery', or unset "
            "ANDROID_MCP_CHECK_SESSIONS to skip this check instead of failing it."
        ) from refused
    sessions = payload.get("value")
    if not isinstance(sessions, list):
        raise AssertionError(f"Appium refused to list sessions: {payload}")
    return len(sessions)


def structured_payload(result: object) -> dict[str, object]:
    """Read structured MCP output across the in-memory and stdio clients."""

    payload = result.model_dump(by_alias=True)
    structured = payload["structuredContent"]
    assert isinstance(structured, dict)
    return structured


def visible_package(ui_tree: str) -> str:
    """Extract the first Android package named by a UI dump."""

    root = element_tree.fromstring(ui_tree)
    for node in root.iter("node"):
        package = node.attrib.get("package")
        if package:
            return package
    raise AssertionError("The UI tree did not name a visible package.")


def reset_to_a_known_screen() -> None:
    """Put Android back on the home screen with Settings not running.

    One case used to be able to explain the next: a run that left the keyboard
    up or the Settings search open changed what the following case found, and
    FLOW-NAV-1 failed once for that reason and passed alone.

    This only establishes a starting point. It navigates nothing the campaign is
    meant to prove: `settings.open_apps` still has to reach Apps by itself, and
    no promise is relaxed to accommodate a dirty screen. Doing it through ADB
    rather than the harness is deliberate too — the fixture must not depend on
    the very tools it is preparing the ground for.
    """

    adb = resolve_adb_path()
    for arguments in (
        ["shell", "input", "keyevent", "KEYCODE_HOME"],
        ["shell", "am", "force-stop", "com.android.settings"],
        # The search bar lives in a second package, and it is the one that was
        # leaving a text field focused behind it.
        ["shell", "am", "force-stop", "com.google.android.settings.intelligence"],
    ):
        subprocess.run(
            [adb, "-s", "emulator-5554", *arguments],
            check=False,
            capture_output=True,
            timeout=20,
        )


@unittest.skipUnless(
    RUN_EMULATOR_ECA,
    "Set ANDROID_MCP_RUN_EMULATOR=1 to run the disposable-emulator ECA campaign.",
)
class McpEmulatorEcaTests(unittest.IsolatedAsyncioTestCase):
    """Verify the business promises of the MCP server against the real AVD."""

    async def asyncSetUp(self) -> None:
        await asyncio.to_thread(reset_to_a_known_screen)
        await asyncio.sleep(1)

    async def test_observation_is_real_and_does_not_navigate(self) -> None:
        """INV-OBS-1: status, tree and capture leave the foreground UI unchanged."""

        async with Client(build_server()) as client:
            before = structured_payload(await client.call_tool("ui.get_tree"))
            status = structured_payload(await client.call_tool("emulator.get_status"))
            capture = structured_payload(await client.call_tool("screen.capture"))
            after = structured_payload(await client.call_tool("ui.get_tree"))

        self.assertTrue(before["ok"], before.get("error"))
        self.assertTrue(status["ok"], status.get("error"))
        self.assertTrue(capture["ok"], capture.get("error"))
        self.assertTrue(after["ok"], after.get("error"))
        self.assertEqual(status["data"]["udid"], "emulator-5554")
        self.assertTrue(status["data"]["android_version"])
        self.assertTrue(status["data"]["appium_version"])
        self.assertTrue(capture["data"]["captured"])
        self.assertEqual(
            before["data"]["foreground_package"],
            after["data"]["foreground_package"],
        )

        evidence = capture["evidence"]
        self.assertIsNotNone(evidence)
        evidence_path = PROJECT_ROOT / evidence["path"]
        self.assertTrue(evidence_path.is_file(), evidence_path)

    async def test_declared_navigation_reaches_apps_with_evidence(self) -> None:
        """FLOW-NAV-1: the sole mutation ends on Settings Apps and records proof."""

        async with Client(build_server()) as client:
            navigation = structured_payload(await client.call_tool("settings.open_apps"))
            tree = structured_payload(await client.call_tool("ui.get_tree"))

        self.assertTrue(navigation["ok"], navigation.get("error"))
        self.assertIn("All apps", navigation["data"]["screen_marker"])
        self.assertTrue(tree["ok"], tree.get("error"))
        self.assertEqual(tree["data"]["foreground_package"], "com.android.settings")
        self.assertIn("All apps", tree["data"]["texts"])

        evidence = navigation["evidence"]
        self.assertIsNotNone(evidence)
        self.assertTrue((PROJECT_ROOT / evidence["path"]).is_file())

    async def test_two_captures_keep_distinct_evidence(self) -> None:
        """SEQ-EVID-1: retries must not overwrite an earlier screenshot."""

        async with Client(build_server()) as client:
            first = structured_payload(await client.call_tool("screen.capture"))
            second = structured_payload(await client.call_tool("screen.capture"))

        self.assertTrue(first["ok"], first.get("error"))
        self.assertTrue(second["ok"], second.get("error"))
        self.assertNotEqual(
            first["evidence"]["artifact_id"],
            second["evidence"]["artifact_id"],
        )
        self.assertTrue((PROJECT_ROOT / first["evidence"]["path"]).is_file())
        self.assertTrue((PROJECT_ROOT / second["evidence"]["path"]).is_file())

    async def test_stdio_process_exposes_the_same_catalog_and_status(self) -> None:
        """CONTRACT-STDIO-1: a separate MCP process answers over actual stdio."""

        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(PROJECT_ROOT)
        server = StdioServerParameters(
            command=sys.executable,
            args=["-m", "entradas.mcp.server"],
            cwd=str(PROJECT_ROOT),
            env=environment,
        )
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                catalog = await session.list_tools()
                result = await session.call_tool(
                    "emulator.get_status", read_timeout_seconds=15
                )

        self.assertEqual(
            {tool.name for tool in catalog.tools},
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
        payload = structured_payload(result)
        self.assertTrue(payload["ok"], payload.get("error"))
        self.assertEqual(payload["tool"], "emulator.get_status")

    async def test_semantic_navigation_controls_settings_without_coordinates(self) -> None:
        """FLOW-UI-1: open, tap, scroll and back work through semantic MCP actions."""

        async with Client(build_server()) as client:
            packages = structured_payload(await client.call_tool("app.list_installed"))
            settings_apps = structured_payload(
                await client.call_tool("settings.open_apps")
            )
            tapped = structured_payload(
                await client.call_tool("ui.tap", {"selector": {"text": "Calendar"}})
            )
            scrolled = structured_payload(
                await client.call_tool("ui.scroll", {"direction": "down"})
            )
            backed = structured_payload(await client.call_tool("device.back"))

        self.assertTrue(packages["ok"], packages.get("error"))
        self.assertIn("com.android.settings", packages["data"]["packages"])
        self.assertTrue(settings_apps["ok"], settings_apps.get("error"))
        self.assertTrue(tapped["ok"], tapped.get("error"))
        self.assertEqual(tapped["data"]["target"], {"text": "Calendar"})
        self.assertTrue(scrolled["ok"], scrolled.get("error"))
        self.assertEqual(scrolled["data"]["direction"], "down")
        self.assertTrue(backed["ok"], backed.get("error"))
        self.assertEqual(backed["data"]["foreground_package"], "com.android.settings")

        for payload in (settings_apps, tapped, scrolled, backed):
            self.assertTrue((PROJECT_ROOT / payload["evidence"]["path"]).is_file())

    async def test_semantic_text_input_reaches_a_real_settings_search_field(self) -> None:
        """FLOW-TEXT-1: semantic tap then text input works across MCP actions."""

        async with Client(build_server()) as client:
            await client.call_tool("settings.open_apps")
            opened_search = structured_payload(
                await client.call_tool(
                    "ui.tap",
                    {
                        "selector": {
                            "content_desc": "Search"
                        }
                    },
                )
            )
            typed = structured_payload(
                await client.call_tool(
                    "ui.type_text",
                    {
                        "selector": {
                            "input_hint": "Search"
                        },
                        "text": "Apps",
                    },
                )
            )
            tree = structured_payload(await client.call_tool("ui.get_tree"))

        self.assertTrue(opened_search["ok"], opened_search.get("error"))
        self.assertTrue(typed["ok"], typed.get("error"))
        self.assertEqual(typed["data"]["characters_sent"], 4)
        self.assertTrue(
            any("Apps" in text for text in tree["data"]["texts"]),
            tree["data"]["texts"][:20],
        )
        self.assertTrue((PROJECT_ROOT / typed["evidence"]["path"]).is_file())

    async def test_explicit_ui_flow_keeps_input_state_then_releases_the_driver(self) -> None:
        """FLOW-CHAIN-1: write through one lease, then release it explicitly."""

        async with Client(build_server()) as client:
            await client.call_tool("settings.open_apps")
            opened = structured_payload(await client.call_tool("ui.session.open"))
            session_id = opened["data"]["session_id"]
            try:
                tapped = structured_payload(
                    await client.call_tool(
                        "ui.tap",
                        {
                            "selector": {"content_desc": "Search"},
                            "session_id": session_id,
                        },
                    )
                )
                typed = structured_payload(
                    await client.call_tool(
                        "ui.type_text",
                        {
                            "selector": {"input_hint": "Search"},
                            "text": "Apps",
                            "session_id": session_id,
                        },
                    )
                )
                tree = structured_payload(
                    await client.call_tool("ui.get_tree", {"session_id": session_id})
                )
            finally:
                closed = structured_payload(
                    await client.call_tool("ui.session.close", {"session_id": session_id})
                )

        self.assertTrue(opened["ok"], opened.get("error"))
        self.assertTrue(tapped["ok"], tapped.get("error"))
        self.assertTrue(typed["ok"], typed.get("error"))
        self.assertTrue(tree["ok"], tree.get("error"))
        self.assertTrue(closed["ok"], closed.get("error"))
        self.assertEqual(typed["data"]["characters_sent"], 4)
        self.assertTrue(any("Apps" in text for text in tree["data"]["texts"]))

    async def test_every_reachable_tree_selector_resolves(self) -> None:
        """FLOW-SEL-ALL-1: every actionable selector reaches a real element.

        This closes the loop the harness exists for: the model reads the screen
        and gets back the exact vocabulary it must speak, with no XML parsing,
        no coordinates and no guessing on its side. The driver stays on the
        same stable Settings screen: clicking each offered target would change
        that screen and would only prove the first one.
        """

        async with Client(build_server()) as client:
            opened = structured_payload(await client.call_tool("settings.open_apps"))
            tree = structured_payload(await client.call_tool("ui.get_tree"))

        self.assertTrue(opened["ok"], opened.get("error"))
        self.assertTrue(tree["ok"], tree.get("error"))
        offered = [
            action
            for action in tree["data"]["actions"]
            if action["enabled"]
            and not action.get("ambiguous")
            and not action.get("covered_by_keyboard")
        ]
        self.assertTrue(offered, "Settings offered no reachable semantic targets")

        config = SettingsDemoConfig(
            appium_url=os.getenv("APPIUM_URL", "http://127.0.0.1:4723"),
            udid=os.getenv("ANDROID_UDID", "emulator-5554"),
            connect_timeout_seconds=int(
                os.getenv("ANDROID_MCP_CONNECT_TIMEOUT", "120")
            ),
        )
        driver = await asyncio.to_thread(create_device_driver, config)
        try:
            for action in offered:
                selector = action["selector"]
                with self.subTest(selector=selector, role=action["role"]):
                    element = await asyncio.to_thread(
                        find_element, driver, validate_selector(selector)
                    )
                    self.assertTrue(element.is_displayed())
        finally:
            await asyncio.to_thread(close_driver, driver)

    async def test_the_summary_is_far_cheaper_than_the_raw_dump(self) -> None:
        """The dump stays reachable, but looking at the screen stops costing it."""

        async with Client(build_server()) as client:
            summary = structured_payload(await client.call_tool("ui.get_tree"))
            verbose = structured_payload(
                await client.call_tool("ui.get_tree", {"include_raw": True})
            )

        raw_size = len(verbose["data"]["ui_tree"])
        summary_size = len(json.dumps(summary["data"]))
        self.assertNotIn("ui_tree", summary["data"])
        self.assertLess(summary_size, raw_size)

    @unittest.skipUnless(
        CHECK_SESSIONS,
        "Set ANDROID_MCP_CHECK_SESSIONS=1 with Appium started using "
        "--allow-insecure=session_discovery.",
    )
    async def test_no_appium_session_survives_a_success_or_a_failure(self) -> None:
        """INV-SESION-1: every action closes its session, including when it fails."""

        before = open_appium_sessions()
        async with Client(build_server()) as client:
            await client.call_tool("settings.open_apps")
            await client.call_tool("ui.scroll", {"direction": "down"})
            await client.call_tool(
                "ui.tap", {"selector": {"text": "NO_EXISTE_ECA_XYZ"}}
            )
            await client.call_tool("device.back")

        self.assertEqual(open_appium_sessions(), before)

    @unittest.skipUnless(
        TARGET_APP_PACKAGE,
        "Set ANDROID_MCP_ECA_TARGET_PACKAGE to test a launchable target app.",
    )
    async def test_launchable_target_app_is_opened_and_observable(self) -> None:
        """FLOW-APP-1: a declared app package opens and appears in the MCP UI tree."""

        async with Client(build_server()) as client:
            opened = structured_payload(
                await client.call_tool(
                    "app.open", {"package_name": TARGET_APP_PACKAGE}
                )
            )
            tree = structured_payload(await client.call_tool("ui.get_tree"))

        self.assertTrue(opened["ok"], opened.get("error"))
        self.assertEqual(opened["data"]["foreground_package"], TARGET_APP_PACKAGE)
        self.assertEqual(tree["data"]["foreground_package"], TARGET_APP_PACKAGE)
        self.assertTrue((PROJECT_ROOT / opened["evidence"]["path"]).is_file())
