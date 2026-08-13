"""
SUME DOCBLOCK

Nombre: demo_settings
Tipo: Lógica

Entradas:
- SettingsDemoConfig.

Acciones:
- Orquesta una única demostración Settings -> Apps usando módulos especializados.

Salidas:
- SettingsDemoResult normalizado, con evidencia de éxito o fallo.
"""

from __future__ import annotations

from typing import Any

from contratos.demo_settings import SettingsDemoConfig, SettingsDemoResult
from contratos.mcp import HarnessError
from logica.evidencias.capturas import save_screenshot
from logica.navegacion.ajustes import (
    SettingsForegroundError,
    UiElementNotFoundError,
    assert_settings_foreground,
    navigate_to_apps,
)
from logica.sesiones.appium import close_driver, create_settings_driver


def run_settings_demo(config: SettingsDemoConfig) -> SettingsDemoResult:
    """Execute one safe emulator-only navigation flow end to end."""

    driver: Any | None = None
    try:
        driver = create_settings_driver(config)
        assert_settings_foreground(driver)
        marker = navigate_to_apps(driver)
        screenshot = save_screenshot(driver, "settings-apps")
        return SettingsDemoResult(True, marker, str(screenshot))
    except Exception as exc:
        screenshot_path: str | None = None
        if driver is not None:
            try:
                screenshot_path = str(save_screenshot(driver, "failure"))
            except Exception:
                screenshot_path = None
        error_code = "INTERNAL_ERROR"
        if isinstance(exc, HarnessError):
            # A guard already classified this failure; keep its typed code instead
            # of flattening a refused emulator or endpoint into INTERNAL_ERROR.
            error_code = exc.code.value
        elif isinstance(exc, SettingsForegroundError):
            error_code = "SETTINGS_FOREGROUND_FAILED"
        elif isinstance(exc, UiElementNotFoundError):
            error_code = "UI_ELEMENT_NOT_FOUND"
        return SettingsDemoResult(
            False,
            f"{type(exc).__name__}: {exc}",
            screenshot_path,
            error_code,
        )
    finally:
        if driver is not None:
            close_driver(driver)
