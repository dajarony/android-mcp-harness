"""Regressions for explicit, short-lived chains of Android UI actions."""

from time import monotonic
import unittest
from unittest.mock import patch

from contratos.demo_settings import SettingsDemoConfig
from contratos.mcp import HarnessError, McpErrorCode
from logica.sesiones.flujo import UiFlowSessions


CONFIG = SettingsDemoConfig("http://127.0.0.1:4723", "emulator-5554")


class UiFlowSessionTests(unittest.IsolatedAsyncioTestCase):
    """A flow is exclusive, opaque and always ends by close or expiry."""

    async def test_matching_token_reuses_one_driver_until_explicit_close(self) -> None:
        driver = object()
        with patch("logica.sesiones.flujo.create_device_driver", return_value=driver), patch(
            "logica.sesiones.flujo.close_driver"
        ) as close_driver:
            flows = UiFlowSessions(60)
            session_id = await flows.open(CONFIG)

            async with flows.use(session_id) as borrowed:
                self.assertIs(borrowed, driver)

            self.assertFalse(close_driver.called)
            await flows.close(session_id)

        close_driver.assert_called_once_with(driver)

    async def test_second_flow_is_rejected_without_opening_another_driver(self) -> None:
        with patch("logica.sesiones.flujo.create_device_driver", return_value=object()) as create_driver, patch(
            "logica.sesiones.flujo.close_driver"
        ):
            flows = UiFlowSessions(60)
            session_id = await flows.open(CONFIG)
            with self.assertRaises(HarnessError) as raised:
                await flows.open(CONFIG)
            await flows.close(session_id)

        self.assertEqual(raised.exception.code, McpErrorCode.EMULATOR_BUSY)
        self.assertEqual(create_driver.call_count, 1)

    async def test_expired_flow_closes_before_a_new_owner_is_allowed(self) -> None:
        first_driver = object()
        second_driver = object()
        with patch(
            "logica.sesiones.flujo.create_device_driver",
            side_effect=[first_driver, second_driver],
        ), patch("logica.sesiones.flujo.close_driver") as close_driver:
            flows = UiFlowSessions(60)
            await flows.open(CONFIG)
            assert flows._active is not None
            flows._active.expires_at = monotonic() - 1

            second_session_id = await flows.open(CONFIG)

            await flows.close(second_session_id)

        self.assertEqual(close_driver.call_count, 2)
        close_driver.assert_any_call(first_driver)
        close_driver.assert_any_call(second_driver)

    async def test_wrong_or_malformed_token_cannot_borrow_or_close_the_flow(self) -> None:
        with patch("logica.sesiones.flujo.create_device_driver", return_value=object()), patch(
            "logica.sesiones.flujo.close_driver"
        ):
            flows = UiFlowSessions(60)
            session_id = await flows.open(CONFIG)
            wrong_id = "x" * len(session_id)

            with self.assertRaises(HarnessError) as malformed:
                await flows.close("not-a-session")
            with self.assertRaises(HarnessError) as wrong:
                async with flows.use(wrong_id):
                    pass

            await flows.close(session_id)

        self.assertEqual(malformed.exception.code, McpErrorCode.INVALID_UI_SESSION)
        self.assertEqual(wrong.exception.code, McpErrorCode.INVALID_UI_SESSION)
