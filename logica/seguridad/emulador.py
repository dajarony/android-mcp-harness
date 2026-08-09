"""
SUME DOCBLOCK

Nombre: emulador
Tipo: Lógica

Entradas:
- UDID configurado para el arnés Android.

Acciones:
- Rechaza identificadores que no pertenecen a un emulador Android.

Salidas:
- UDID validado o HarnessError antes de cualquier llamada a ADB/Appium.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from contratos.mcp import HarnessError, McpErrorCode


_EMULATOR_UDID = re.compile(r"^emulator-\d+$")


def assert_emulator_udid(udid: str) -> str:
    """Accept only the standard ADB identifier shape for Android emulators."""

    if not _EMULATOR_UDID.fullmatch(udid):
        raise HarnessError(
            McpErrorCode.EMULATOR_UNAVAILABLE,
            "Configured ANDROID_UDID is not an Android emulator identifier.",
        )
    return udid


def assert_local_appium_url(appium_url: str) -> str:
    """Accept only a loopback HTTP endpoint for the local Appium bridge."""

    parsed = urlparse(appium_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise HarnessError(
            McpErrorCode.APPIUM_UNAVAILABLE,
            "APPIUM_URL must point to a local loopback HTTP endpoint.",
        )
    return appium_url
