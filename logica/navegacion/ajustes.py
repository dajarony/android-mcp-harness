"""
SUME DOCBLOCK

Nombre: ajustes
Tipo: Lógica

Entradas:
- Una sesión Appium ya conectada a Android Settings.

Acciones:
- Comprueba el paquete visible y navega desde Ajustes a Apps.

Salidas:
- Texto marcador de la pantalla Apps o un error explícito.
"""

from __future__ import annotations

from typing import Any

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait


def assert_settings_foreground(driver: Any) -> None:
    """Fail if the active application is not Android Settings."""

    if driver.current_package != "com.android.settings":
        raise RuntimeError(
            f"Expected Settings foreground package, got {driver.current_package!r}"
        )


def navigate_to_apps(driver: Any) -> str:
    """Open Apps and return its Android-version-specific screen marker."""

    apps = WebDriverWait(driver, 20).until(
        lambda current: current.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("Apps")',
        )
    )
    apps.click()
    marker = WebDriverWait(driver, 10).until(
        lambda current: current.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("See all")',
        )
    )
    return marker.text
