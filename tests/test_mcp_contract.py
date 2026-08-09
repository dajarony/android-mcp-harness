"""Unit regressions for MCP response and exclusivity contracts."""

import unittest

from contratos.mcp import HarnessError, McpErrorCode, McpToolResult
from contratos.demo_settings import SettingsDemoConfig
from logica.servicios.mcp_server.controller import AndroidMcpController
from logica.servicios.mcp_server.gate import EmulatorOperationGate


class McpContractTests(unittest.IsolatedAsyncioTestCase):
    def test_failure_never_reports_success_or_exposes_a_traceback(self) -> None:
        result = McpToolResult.failure(
            "ui.get_tree",
            HarnessError(McpErrorCode.UI_TREE_UNAVAILABLE, "Android returned no XML."),
        ).to_dict()

        self.assertFalse(result["ok"])
        self.assertEqual(result["data"], {})
        self.assertEqual(result["error"]["code"], "UI_TREE_UNAVAILABLE")
        self.assertNotIn("traceback", str(result).lower())

    async def test_gate_rejects_a_second_concurrent_operation(self) -> None:
        gate = EmulatorOperationGate()

        async with gate.acquire():
            with self.assertRaises(HarnessError) as raised:
                async with gate.acquire():
                    pass

        self.assertEqual(raised.exception.code, McpErrorCode.EMULATOR_BUSY)
        self.assertFalse(gate.is_busy)

    async def test_physical_device_identifier_is_rejected_before_any_adapter(self) -> None:
        """INV-SAFE-1: the MCP controller never accepts a physical-device UDID."""

        controller = AndroidMcpController(
            SettingsDemoConfig(
                appium_url="http://127.0.0.1:4723",
                udid="physical-device-01",
            )
        )

        result = await controller.get_emulator_status()

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "EMULATOR_UNAVAILABLE")
        self.assertEqual(result["data"], {})
