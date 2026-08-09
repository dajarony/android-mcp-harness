"""ECA campaign against the disposable Android emulator and real MCP transports.

This suite is opt-in because it requires the local Android SDK, an online AVD and
an Appium server.  It never accepts a physical-device UDID and only navigates the
emulator through the declared Settings flow.
"""

from __future__ import annotations

import os
import sys
import unittest
import xml.etree.ElementTree as element_tree
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client import Client
from mcp.client.stdio import stdio_client

from entradas.mcp.server import build_server


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_EMULATOR_ECA = os.getenv("ANDROID_MCP_RUN_EMULATOR") == "1"


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


@unittest.skipUnless(
    RUN_EMULATOR_ECA,
    "Set ANDROID_MCP_RUN_EMULATOR=1 to run the disposable-emulator ECA campaign.",
)
class McpEmulatorEcaTests(unittest.IsolatedAsyncioTestCase):
    """Verify the business promises of the MCP server against the real AVD."""

    async def test_observation_is_real_and_does_not_navigate(self) -> None:
        """INV-OBS-1: status, tree and capture leave the foreground UI unchanged."""

        async with Client(build_server()) as client:
            before = structured_payload(await client.call_tool("ui.get_tree"))
            status = structured_payload(await client.call_tool("emulator.get_status"))
            capture = structured_payload(await client.call_tool("screen.capture"))
            after = structured_payload(await client.call_tool("ui.get_tree"))

        self.assertTrue(before["ok"])
        self.assertTrue(status["ok"])
        self.assertTrue(capture["ok"])
        self.assertTrue(after["ok"])
        self.assertEqual(status["data"]["udid"], "emulator-5554")
        self.assertTrue(status["data"]["android_version"])
        self.assertTrue(status["data"]["appium_version"])
        self.assertTrue(capture["data"]["captured"])
        self.assertEqual(
            visible_package(before["data"]["ui_tree"]),
            visible_package(after["data"]["ui_tree"]),
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

        self.assertTrue(navigation["ok"])
        self.assertIn("See all", navigation["data"]["screen_marker"])
        self.assertTrue(tree["ok"])
        self.assertEqual(visible_package(tree["data"]["ui_tree"]), "com.android.settings")
        self.assertIn("Apps", tree["data"]["ui_tree"])

        evidence = navigation["evidence"]
        self.assertIsNotNone(evidence)
        self.assertTrue((PROJECT_ROOT / evidence["path"]).is_file())

    async def test_two_captures_keep_distinct_evidence(self) -> None:
        """SEQ-EVID-1: retries must not overwrite an earlier screenshot."""

        async with Client(build_server()) as client:
            first = structured_payload(await client.call_tool("screen.capture"))
            second = structured_payload(await client.call_tool("screen.capture"))

        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
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
            },
        )
        payload = structured_payload(result)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["tool"], "emulator.get_status")
