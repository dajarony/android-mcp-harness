"""
SUME DOCBLOCK

Nombre: lanzador
Tipo: Lógica

Entradas:
- UDID de emulador y paquete Android previamente validado.

Acciones:
- Resuelve exclusivamente la actividad MAIN/LAUNCHER y la inicia mediante ADB.

Salidas:
- Paquete lanzado o HarnessError APP_NOT_FOUND sin shell arbitrario.
"""

from __future__ import annotations

import subprocess

from contratos.mcp import HarnessError, McpErrorCode
from contratos.ui_control import validate_package_name
from logica.infraestructura.adb import resolve_adb_path
from logica.seguridad.emulador import assert_emulator_udid


def launch_package(udid: str, package_name: object) -> str:
    """Start the package's declared launcher component, never a caller command."""

    package = validate_package_name(package_name)
    assert_emulator_udid(udid)
    component = _resolve_launcher_component(udid, package)
    _run_launcher_command(udid, ["shell", "am", "start", "-W", "-n", component])
    return package


def start_settings_apps(udid: str) -> None:
    """Open Android's fixed Apps settings intent for the declared demo flow."""

    assert_emulator_udid(udid)
    _run_launcher_command(
        udid,
        ["shell", "am", "start", "-W", "-S", "-a", "android.settings.APPLICATION_SETTINGS"],
    )


def _resolve_launcher_component(udid: str, package: str) -> str:
    """Ask Android for its trusted MAIN/LAUNCHER component for one package."""

    output = _run_launcher_command(
        udid,
        [
            "shell",
            "cmd",
            "package",
            "resolve-activity",
            "--brief",
            "-a",
            "android.intent.action.MAIN",
            "-c",
            "android.intent.category.LAUNCHER",
            package,
        ],
    )
    lines = output.decode("utf-8", errors="replace").strip().splitlines()
    components = [line for line in lines if line.startswith(f"{package}/")]
    if len(components) != 1:
        raise HarnessError(
            McpErrorCode.APP_NOT_FOUND,
            "The requested package has no launchable Android activity.",
        )
    return components[0]


def _run_launcher_command(udid: str, arguments: list[str]) -> bytes:
    """Run one of the two hard-coded launcher commands without a system shell."""

    try:
        completed = subprocess.run(
            [resolve_adb_path(), "-s", udid, *arguments],
            check=False,
            capture_output=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HarnessError(
            McpErrorCode.EMULATOR_UNAVAILABLE,
            "The configured Android emulator did not respond while launching the package.",
        ) from exc
    if completed.returncode != 0:
        raise HarnessError(
            McpErrorCode.APP_NOT_FOUND,
            "The requested package could not be launched in the configured emulator.",
        )
    return completed.stdout
