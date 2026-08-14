"""
SUME DOCBLOCK

Nombre: adb
Tipo: Lógica

Entradas:
- UDID validado de un emulador Android.

Acciones:
- Ejecuta únicamente consultas ADB de solo lectura codificadas en este módulo.

Salidas:
- Disponibilidad, propiedades, árbol UI o bytes PNG del emulador.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from contratos.mcp import HarnessError, McpErrorCode
from logica.evidencias.imagen import assert_png_shows_something
from logica.seguridad.emulador import assert_emulator_udid


# Android publishes the keyboard as a window inset, one line per source.
_IME_INSET = re.compile(
    r"type=ime\s+frame=\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\][^\n]*?\svisible=(true|false)"
)


def resolve_adb_path() -> str:
    """Resolve the local ADB executable without accepting caller-provided paths."""

    android_home = os.getenv("ANDROID_HOME") or os.getenv("ANDROID_SDK_ROOT")
    if android_home:
        platform_tools = Path(android_home) / "platform-tools"
        # The binary was hard-coded as adb.exe, so on Linux and macOS the SDK
        # path silently never matched and only the PATH lookup below ever worked.
        for name in ("adb.exe", "adb"):
            executable = platform_tools / name
            if executable.is_file():
                return str(executable)
    executable = shutil.which("adb")
    if executable:
        return executable
    raise HarnessError(
        McpErrorCode.EMULATOR_UNAVAILABLE,
        "ADB was not found. Set ANDROID_HOME or add platform-tools to PATH.",
    )


def _run_read_only_adb(udid: str, arguments: list[str], timeout_seconds: int) -> bytes:
    """Run one fixed read-only ADB command without shell interpolation."""

    assert_emulator_udid(udid)
    try:
        completed = subprocess.run(
            [resolve_adb_path(), "-s", udid, *arguments],
            check=False,
            capture_output=True,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HarnessError(
            McpErrorCode.EMULATOR_UNAVAILABLE,
            "The configured Android emulator did not respond to ADB.",
        ) from exc
    if completed.returncode != 0:
        raise HarnessError(
            McpErrorCode.EMULATOR_UNAVAILABLE,
            "The configured Android emulator is unavailable in ADB.",
        )
    return completed.stdout


def assert_emulator_connected(udid: str) -> None:
    """Verify that the configured emulator is listed as an online ADB device."""

    devices = _run_read_only_adb(udid, ["get-state"], timeout_seconds=5)
    if devices.decode("utf-8", errors="replace").strip() != "device":
        raise HarnessError(
            McpErrorCode.EMULATOR_UNAVAILABLE,
            "The configured Android emulator is not online.",
        )


def read_emulator_properties(udid: str) -> dict[str, str]:
    """Read only the Android version and model needed by status output."""

    assert_emulator_connected(udid)
    version = _run_read_only_adb(
        udid, ["shell", "getprop", "ro.build.version.release"], 5
    ).decode("utf-8", errors="replace").strip()
    model = _run_read_only_adb(
        udid, ["shell", "getprop", "ro.product.model"], 5
    ).decode("utf-8", errors="replace").strip()
    return {"udid": udid, "android_version": version, "model": model}


def read_installed_packages(udid: str) -> list[str]:
    """Return installed Android package identifiers through one fixed ADB query."""

    output = _run_read_only_adb(udid, ["shell", "pm", "list", "packages"], 10)
    packages = []
    for line in output.decode("utf-8", errors="replace").splitlines():
        if line.startswith("package:"):
            packages.append(line.removeprefix("package:"))
    if not packages:
        raise HarnessError(
            McpErrorCode.EMULATOR_UNAVAILABLE,
            "Android did not return any installed packages.",
        )
    return sorted(packages)


def read_display_density(udid: str) -> int:
    """Read the screen density so layout sizes can be judged in dp, not pixels."""

    output = _run_read_only_adb(udid, ["shell", "wm", "density"], 5).decode(
        "utf-8", errors="replace"
    )
    # "Override density" wins when present, exactly as Android applies it.
    densities = re.findall(r"density:\s*(\d+)", output)
    if not densities:
        raise HarnessError(
            McpErrorCode.EMULATOR_UNAVAILABLE,
            "Android did not report a display density.",
        )
    return int(densities[-1])


def read_keyboard_frame(udid: str) -> tuple[int, int, int, int] | None:
    """Read the on-screen keyboard's rectangle, or None when it is not showing.

    Android publishes it as a window inset, which matters because the keyboard
    is absent from `uiautomator dump`: the dump describes the app window as if
    nothing were over it, so targets behind the keyboard read as available.
    """

    output = _run_read_only_adb(udid, ["shell", "dumpsys", "window"], 15).decode(
        "utf-8", errors="replace"
    )
    for match in _IME_INSET.finditer(output):
        if match.group(5) == "true":
            return tuple(int(value) for value in match.groups()[:4])  # type: ignore[return-value]
    return None


def read_ui_tree(udid: str) -> str:
    """Capture the current UI hierarchy without sending an input event."""

    raw = _run_read_only_adb(
        udid, ["exec-out", "uiautomator", "dump", "/dev/tty"], 10
    ).decode("utf-8", errors="replace")
    start = raw.find("<?xml")
    end = raw.rfind("</hierarchy>")
    if start < 0 or end < 0:
        raise HarnessError(
            McpErrorCode.UI_TREE_UNAVAILABLE,
            "Android did not return a valid UI hierarchy.",
        )
    return raw[start : end + len("</hierarchy>")]


def read_png_screenshot(udid: str) -> bytes:
    """Capture the current screen with ADB without changing its visible state."""

    payload = _run_read_only_adb(udid, ["exec-out", "screencap", "-p"], 10)
    return assert_png_shows_something(payload, "Android")
