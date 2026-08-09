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


@dataclass(frozen=True)
class SettingsDemoResult:
    """Stable outcome returned by the Settings -> Apps flow."""

    succeeded: bool
    detail: str
    screenshot_path: str | None = None
