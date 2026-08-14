"""
SUME DOCBLOCK

Nombre: demo_settings
Tipo: Contrato

Entradas:
- Configuración del endpoint Appium y del emulador Android.
- Resultado normalizado de una demostración.

Acciones:
- Define las estructuras inmutables intercambiadas entre las capas.

Salidas:
- SettingsDemoConfig y SettingsDemoResult sin dependencias de Appium.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SettingsDemoConfig:
    """Connection parameters for the disposable Android emulator."""

    appium_url: str
    udid: str
    # Creating a UiAutomator2 session installs and starts a server APK on the
    # device. Cold, that is 30-60 s, and far more on a shared CI machine. The
    # earlier 10 s budget was measured on a warm laptop and only ever held there.
    connect_timeout_seconds: int = 120
    # A flow session retains an Appium driver only while the client is actively
    # chaining actions. It is not a permanent ownership grant.
    flow_idle_timeout_seconds: int = 60
    # A ceiling, not the declared budget. One UI action is expected to finish
    # well inside 30 s; this is the point past which the harness stops waiting
    # so that a hung Appium command can never hold the emulator for everyone.
    action_timeout_seconds: int = 90


@dataclass(frozen=True)
class SettingsDemoResult:
    """Stable outcome returned by the Settings -> Apps flow."""

    succeeded: bool
    detail: str
    screenshot_path: str | None = None
    error_code: str | None = None
