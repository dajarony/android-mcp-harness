"""Regressions for the setup diagnosis and for finding adb off Windows."""

import unittest
from unittest.mock import patch

from contratos.demo_settings import SettingsDemoConfig
from contratos.diagnostico import Check, CheckState
from contratos.mcp import HarnessError, McpErrorCode
from logica.diagnostico.entorno import inspect_environment
from logica.infraestructura.adb import resolve_adb_path
from salidas.consola.doctor import render_diagnosis


CONFIG = SettingsDemoConfig("http://127.0.0.1:4723", "emulator-5554")


class DiagnosisTests(unittest.TestCase):
    def test_nothing_stops_at_the_first_missing_piece(self) -> None:
        """Reporting one obstacle at a time turns setup into a guessing game."""

        with patch("logica.diagnostico.entorno.shutil.which", return_value=None), patch(
            "logica.diagnostico.entorno.resolve_adb_path",
            side_effect=HarnessError(McpErrorCode.EMULATOR_UNAVAILABLE, "no adb"),
        ), patch(
            "logica.diagnostico.entorno.read_appium_status",
            side_effect=HarnessError(McpErrorCode.APPIUM_UNAVAILABLE, "no appium"),
        ), patch(
            "logica.diagnostico.entorno.assert_emulator_connected",
            side_effect=HarnessError(McpErrorCode.EMULATOR_UNAVAILABLE, "offline"),
        ):
            checks = inspect_environment(CONFIG)

        names = [check.name for check in checks]
        self.assertEqual(len(names), len(set(names)))
        missing = [c.name for c in checks if c.blocks_campaign]
        self.assertEqual(set(missing), {"Java", "ADB", "Emulator", "Appium"})

    def test_every_missing_piece_carries_a_remedy(self) -> None:
        with patch("logica.diagnostico.entorno.shutil.which", return_value=None), patch(
            "logica.diagnostico.entorno.resolve_adb_path",
            side_effect=HarnessError(McpErrorCode.EMULATOR_UNAVAILABLE, "no adb"),
        ), patch(
            "logica.diagnostico.entorno.read_appium_status",
            side_effect=HarnessError(McpErrorCode.APPIUM_UNAVAILABLE, "no appium"),
        ), patch(
            "logica.diagnostico.entorno.assert_emulator_connected",
            side_effect=HarnessError(McpErrorCode.EMULATOR_UNAVAILABLE, "offline"),
        ):
            for check in inspect_environment(CONFIG):
                if check.blocks_campaign:
                    with self.subTest(check=check.name):
                        self.assertTrue(check.remedy.strip())

    def test_a_physical_udid_is_named_as_the_reason(self) -> None:
        checks = inspect_environment(SettingsDemoConfig("http://127.0.0.1:4723", "R3CN90ABCDE"))
        emulator = next(c for c in checks if c.name == "Emulator")

        self.assertTrue(emulator.blocks_campaign)
        self.assertIn("never drives a physical device", emulator.remedy)

    def test_an_optional_piece_never_blocks(self) -> None:
        target = next(c for c in inspect_environment(CONFIG) if c.name == "Target app")
        if target.state is CheckState.OPTIONAL:
            self.assertFalse(target.blocks_campaign)


class ReportTests(unittest.TestCase):
    def test_the_report_says_the_unit_bank_needs_none_of_it(self) -> None:
        report = render_diagnosis(
            [
                Check("Python", CheckState.OK, "3.13.5"),
                Check("Appium", CheckState.MISSING, "not answering", "Start Appium."),
            ]
        )

        self.assertIn("1 of 2 checks block", report)
        self.assertIn("Appium: Start Appium.", report)
        self.assertIn("python -m unittest discover -s tests", report)

    def test_a_healthy_environment_says_so_plainly(self) -> None:
        report = render_diagnosis([Check("Python", CheckState.OK, "3.13.5")])

        self.assertIn("Everything a real campaign needs is present.", report)


class AdbLookupTests(unittest.TestCase):
    """The SDK path was hard-coded to adb.exe, so it never matched off Windows."""

    def test_the_sdk_is_searched_for_the_platform_binary(self) -> None:
        import pathlib

        seen: list[str] = []

        def is_file(self: pathlib.Path) -> bool:
            seen.append(self.name)
            return self.name == "adb"

        with patch.dict("os.environ", {"ANDROID_HOME": "/opt/android"}), patch.object(
            pathlib.Path, "is_file", is_file
        ):
            resolved = resolve_adb_path()

        self.assertIn("adb", seen)
        self.assertTrue(resolved.endswith("adb"))


class JavaVersionTests(unittest.TestCase):
    """Checking that java merely exists is how a setup passes and fails later."""

    def test_both_java_naming_schemes_are_read(self) -> None:
        from logica.diagnostico.entorno import java_major_version

        cases = {
            'java version "1.8.0_491"': 8,
            'openjdk version "17.0.17" 2025-10-21': 17,
            'openjdk version "21.0.1"': 21,
            'java version "1.7.0_80"': 7,
            "no version here": None,
        }
        for reported, expected in cases.items():
            with self.subTest(reported=reported):
                self.assertEqual(java_major_version(reported), expected)

    def test_java_8_is_reported_as_blocking(self) -> None:
        with patch("logica.diagnostico.entorno.shutil.which", return_value="/usr/bin/java"), \
             patch("logica.diagnostico.entorno.subprocess.run") as run:
            run.return_value.stderr = b'java version "1.8.0_491"\n'
            run.return_value.stdout = b""
            java = next(c for c in inspect_environment(CONFIG) if c.name == "Java")

        self.assertTrue(java.blocks_campaign)
        self.assertIn("older than 17", java.detail)

    def test_java_17_passes(self) -> None:
        with patch("logica.diagnostico.entorno.shutil.which", return_value="/usr/bin/java"), \
             patch("logica.diagnostico.entorno.subprocess.run") as run:
            run.return_value.stderr = b'openjdk version "17.0.17" 2025-10-21\n'
            run.return_value.stdout = b""
            java = next(c for c in inspect_environment(CONFIG) if c.name == "Java")

        self.assertEqual(java.state, CheckState.OK)
