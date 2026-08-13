"""Regression tests for contracts and terminal output independent of Android."""

import unittest

from contratos.demo_settings import SettingsDemoConfig, SettingsDemoResult
from salidas.consola.demo_settings import render_demo_result


class ContractBoundaryTests(unittest.TestCase):
    def test_configuration_keeps_connection_boundaries_explicit(self) -> None:
        config = SettingsDemoConfig("http://127.0.0.1:4723", "emulator-5554")

        self.assertEqual(config.appium_url, "http://127.0.0.1:4723")
        self.assertEqual(config.udid, "emulator-5554")

    def test_success_result_includes_evidence_path(self) -> None:
        result = SettingsDemoResult(True, "See all 37 apps", "artifacts/evidence.png")

        self.assertEqual(
            render_demo_result(result),
            "PASS: See all 37 apps; screenshot: artifacts/evidence.png",
        )

    def test_failure_result_never_claims_success(self) -> None:
        """The rendered detail is wording we authored, never a raw exception."""

        result = SettingsDemoResult(
            False, "The Settings Apps marker was not found before timeout."
        )

        self.assertEqual(
            render_demo_result(result),
            "FAIL: The Settings Apps marker was not found before timeout.",
        )
