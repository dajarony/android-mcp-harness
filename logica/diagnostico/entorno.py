"""
SUME DOCBLOCK

Nombre: entorno
Tipo: Lógica

Entradas:
- Configuración local de conexión y variables de entorno.

Acciones:
- Comprueba cada pieza que el arnés necesita y propone su remedio.

Salidas:
- Lista ordenada de Check, de lo más básico a lo más específico.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys

from contratos.demo_settings import SettingsDemoConfig
from contratos.diagnostico import Check, CheckState
from contratos.mcp import HarnessError
from logica.evidencias.capturas import ARTIFACTS
from logica.infraestructura.adb import assert_emulator_connected, resolve_adb_path
from logica.infraestructura.appium import read_appium_status
from logica.seguridad.emulador import assert_emulator_udid


MINIMUM_PYTHON = (3, 12)
# Appium's UiAutomator2 driver requires JDK 17 or newer.
MINIMUM_JAVA = 17


def _python() -> Check:
    version = ".".join(str(part) for part in sys.version_info[:3])
    if sys.version_info[:2] < MINIMUM_PYTHON:
        return Check(
            "Python",
            CheckState.MISSING,
            f"{version} is older than {'.'.join(map(str, MINIMUM_PYTHON))}",
            "Install Python 3.12 or newer and recreate the virtual environment.",
        )
    return Check("Python", CheckState.OK, version)


def _client_packages() -> Check:
    missing = []
    for module in ("appium", "mcp"):
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    if missing:
        return Check(
            "Client packages",
            CheckState.MISSING,
            f"not importable: {', '.join(missing)}",
            "python -m pip install -r requirements.txt",
        )
    return Check("Client packages", CheckState.OK, "appium and mcp importable")


def java_major_version(reported: str) -> int | None:
    """Read the major version from either Java naming scheme.

    Java 8 reports 1.8.0_491 and Java 17 reports 17.0.17. Both appear inside
    quotes on the first line, and the old style hides its real major after a 1.
    """

    match = re.search(r'"(\d+)(?:\.(\d+))?', reported)
    if match is None:
        return None
    major, minor = int(match.group(1)), match.group(2)
    return int(minor) if major == 1 and minor else major


def _java() -> Check:
    java = shutil.which("java")
    remedy = (
        f"Install JDK {MINIMUM_JAVA} and put its bin directory first on PATH, or set "
        "JAVA_HOME. Appium's UiAutomator2 driver cannot start without it."
    )
    if not java:
        return Check("Java", CheckState.MISSING, "java is not on PATH", remedy)
    try:
        finished = subprocess.run(
            [java, "-version"], capture_output=True, timeout=15, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return Check("Java", CheckState.MISSING, "java did not answer", remedy)

    # java -version writes to stderr, which is not an error.
    reported = (finished.stderr or finished.stdout).decode("utf-8", "replace").splitlines()
    first = reported[0] if reported else java
    major = java_major_version(first)
    if major is None:
        return Check("Java", CheckState.MISSING, f"unreadable version: {first}", remedy)
    if major < MINIMUM_JAVA:
        # Checking that java merely exists is how a machine passes this check and
        # then fails to start a session an hour later.
        return Check(
            "Java",
            CheckState.MISSING,
            f"{first} is Java {major}, older than {MINIMUM_JAVA}",
            remedy,
        )
    return Check("Java", CheckState.OK, first)


def _adb() -> Check:
    try:
        return Check("ADB", CheckState.OK, resolve_adb_path())
    except HarnessError as exc:
        return Check(
            "ADB",
            CheckState.MISSING,
            exc.message,
            "Install Android platform-tools and set ANDROID_HOME, or add adb to PATH.",
        )


def _emulator(config: SettingsDemoConfig) -> Check:
    try:
        assert_emulator_udid(config.udid)
    except HarnessError as exc:
        return Check(
            "Emulator",
            CheckState.MISSING,
            exc.message,
            "ANDROID_UDID must name an emulator, such as emulator-5554. This "
            "harness never drives a physical device.",
        )
    try:
        assert_emulator_connected(config.udid)
    except HarnessError as exc:
        return Check(
            "Emulator",
            CheckState.MISSING,
            exc.message,
            f"Start a disposable AVD so that '{config.udid}' comes online: "
            "emulator -avd <name>",
        )
    return Check("Emulator", CheckState.OK, f"{config.udid} online")


def _appium(config: SettingsDemoConfig) -> Check:
    try:
        status = read_appium_status(config.appium_url)
    except HarnessError as exc:
        return Check(
            "Appium",
            CheckState.MISSING,
            exc.message,
            f"Start Appium so it answers at {config.appium_url}: "
            "npm install && ./node_modules/.bin/appium",
        )
    return Check("Appium", CheckState.OK, f"version {status['appium_version']}")


def _evidence_directory() -> Check:
    try:
        ARTIFACTS.mkdir(exist_ok=True)
        probe = ARTIFACTS / ".doctor-write-probe"
        probe.write_bytes(b"")
        probe.unlink()
    except OSError as error:
        return Check(
            "Evidence directory",
            CheckState.MISSING,
            f"{ARTIFACTS} is not writable: {error.strerror}",
            "Grant write permission: without it no action can prove what it did.",
        )
    return Check("Evidence directory", CheckState.OK, str(ARTIFACTS))


def _target_app() -> Check:
    package = os.getenv("ANDROID_MCP_ECA_TARGET_PACKAGE")
    if not package:
        return Check(
            "Target app",
            CheckState.OPTIONAL,
            "ANDROID_MCP_ECA_TARGET_PACKAGE is not set",
            "Set it to a launchable package to also exercise FLOW-APP-1.",
        )
    return Check("Target app", CheckState.OK, package)


def inspect_environment(config: SettingsDemoConfig) -> list[Check]:
    """Check every piece, cheapest first, and never stop at the first failure.

    Reporting one missing thing at a time turns setup into a guessing game. The
    whole picture is more useful than the first obstacle, so nothing here raises.
    """

    return [
        _python(),
        _client_packages(),
        _java(),
        _adb(),
        _emulator(config),
        _appium(config),
        _evidence_directory(),
        _target_app(),
    ]
