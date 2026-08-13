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

import logging
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


LOGGER = logging.getLogger(__name__)

# The cause stays in the local log; the client receives wording we authored.
_PUBLIC_DETAIL = {
    "SETTINGS_FOREGROUND_FAILED": "Android Settings was not the foreground application.",
    "UI_ELEMENT_NOT_FOUND": "The Settings Apps marker was not found before timeout.",
    "INTERNAL_ERROR": "The Settings navigation failed unexpectedly; inspect local evidence and logs.",
}


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
        detail = _PUBLIC_DETAIL["INTERNAL_ERROR"]
        if isinstance(exc, HarnessError):
            # A guard already classified this failure and wrote a safe message;
            # keep both instead of flattening them into INTERNAL_ERROR.
            error_code = exc.code.value
            detail = exc.message
        elif isinstance(exc, SettingsForegroundError):
            error_code = "SETTINGS_FOREGROUND_FAILED"
            detail = _PUBLIC_DETAIL[error_code]
        elif isinstance(exc, UiElementNotFoundError):
            error_code = "UI_ELEMENT_NOT_FOUND"
            detail = _PUBLIC_DETAIL[error_code]
        LOGGER.exception("Settings navigation failed with %s", error_code)
        return SettingsDemoResult(False, detail, screenshot_path, error_code)
    finally:
        if driver is not None:
            close_driver(driver)
