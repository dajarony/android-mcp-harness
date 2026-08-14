"""Unit regressions for the external, declarative MCP reference client."""

import unittest

from contratos.cliente_referencia import parse_reference_flow
from contratos.mcp import HarnessError
from logica.servicios.cliente_referencia.runner import run_reference_flow


FLOW = parse_reference_flow(
    {
        "package_name": "com.example.flutterapp",
        "steps": [
            {"tool": "ui.tap", "arguments": {"selector": {"text": "Search"}}},
            {
                "tool": "ui.type_text",
                "arguments": {"selector": {"input_hint": "Search"}, "text": "hello"},
            },
        ],
    }
)


class ReferenceFlowContractTests(unittest.TestCase):
    def test_client_owns_the_flow_session_token(self) -> None:
        with self.assertRaises(HarnessError) as raised:
            parse_reference_flow(
                {
                    "package_name": "com.example.app",
                    "steps": [
                        {
                            "tool": "ui.tap",
                            "arguments": {
                                "selector": {"text": "Save"},
                                "session_id": "caller-controlled",
                            },
                        }
                    ],
                }
            )
        self.assertEqual(raised.exception.code.value, "INVALID_SELECTOR")


class ReferenceRunnerTests(unittest.IsolatedAsyncioTestCase):
    async def test_declared_steps_receive_the_client_owned_session_and_close_it(self) -> None:
        calls: list[tuple[str, dict[str, object]]] = []
        responses = iter(
            [
                {"ok": True, "data": {"opened_package": FLOW.package_name}},
                {"ok": True, "data": {"actions": []}},
                {"ok": True, "data": {"session_id": "x" * 32}},
                {"ok": True, "data": {}, "evidence": {"artifact_id": "tap"}},
                {"ok": True, "data": {}, "evidence": {"artifact_id": "type"}},
                {"ok": True, "data": {"closed": True}},
                {"ok": True, "data": {"texts": ["hello"]}},
            ]
        )

        async def call(tool: str, arguments: dict[str, object]) -> dict[str, object]:
            calls.append((tool, arguments))
            return next(responses)

        run = await run_reference_flow(call, FLOW)

        self.assertTrue(run.ok)
        self.assertTrue(run.session_closed)
        self.assertEqual(
            [tool for tool, _ in calls],
            [
                "app.open",
                "ui.get_tree",
                "ui.session.open",
                "ui.tap",
                "ui.type_text",
                "ui.session.close",
                "ui.get_tree",
            ],
        )
        self.assertEqual(calls[3][1]["session_id"], "x" * 32)
        self.assertEqual(calls[4][1]["session_id"], "x" * 32)

    async def test_failed_action_still_closes_the_session_and_stops_the_recipe(self) -> None:
        calls: list[str] = []
        responses = iter(
            [
                {"ok": True, "data": {}},
                {"ok": True, "data": {}},
                {"ok": True, "data": {"session_id": "x" * 32}},
                {"ok": False, "error": {"code": "UI_ELEMENT_NOT_FOUND", "message": "missing"}},
                {"ok": True, "data": {"closed": True}},
                {"ok": True, "data": {}},
            ]
        )

        async def call(tool: str, arguments: dict[str, object]) -> dict[str, object]:
            calls.append(tool)
            return next(responses)

        run = await run_reference_flow(call, FLOW)

        self.assertFalse(run.ok)
        self.assertTrue(run.session_closed)
        self.assertEqual(run.error["code"], "UI_ELEMENT_NOT_FOUND")
        self.assertEqual(calls.count("ui.type_text"), 0)
        self.assertIn("ui.session.close", calls)
