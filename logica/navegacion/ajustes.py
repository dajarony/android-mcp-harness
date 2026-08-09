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
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait


class SettingsForegroundError(RuntimeError):
    """Android Settings was not the active application after session startup."""


class UiElementNotFoundError(RuntimeError):
    """A required semantic Android Settings element was not found in time."""


def assert_settings_foreground(driver: Any) -> None:
    """Fail if the active application is not Android Settings."""

    if driver.current_package != "com.android.settings":
        raise SettingsForegroundError(
            f"Expected Settings foreground package, got {driver.current_package!r}"
        )


def navigate_to_apps(driver: Any) -> str:
    """Open Apps and return its Android-version-specific screen marker."""

    try:
        apps = WebDriverWait(driver, 10).until(
            lambda current: current.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiSelector().textContains("Apps")',
            )
        )
        apps.click()
        marker = WebDriverWait(driver, 8).until(
            lambda current: current.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiSelector().textContains("See all")',
            )
        )
    except TimeoutException as exc:
        raise UiElementNotFoundError(
            "Required semantic Settings element was not found before timeout"
        ) from exc
    return marker.text
