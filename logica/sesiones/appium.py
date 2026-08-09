"""
SUME DOCBLOCK

Nombre: appium
Tipo: Lógica

Entradas:
- SettingsDemoConfig con URL de Appium y UDID del emulador.

Acciones:
- Crea y cierra una sesión UiAutomator2 de Appium.

Salidas:
- Driver conectado exclusivamente al emulador configurado.
"""

from __future__ import annotations

from typing import Any

from appium import webdriver
from appium.webdriver.client_config import AppiumClientConfig
from appium.options.android import UiAutomator2Options

from contratos.demo_settings import SettingsDemoConfig


def create_settings_driver(config: SettingsDemoConfig) -> Any:
    """Connect one Appium session and bring Android Settings to foreground."""

    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.automation_name = "UiAutomator2"
    options.device_name = "Android Emulator"
    options.udid = config.udid
    options.app_package = "com.android.settings"
    options.app_activity = ".Settings"
    options.no_reset = True
    options.set_capability("appium:forceAppLaunch", True)
    options.new_command_timeout = 60
    client_config = AppiumClientConfig(
        remote_server_addr=config.appium_url,
        timeout=10,
        direct_connection=False,
    )
    return webdriver.Remote(options=options, client_config=client_config)


def close_driver(driver: Any) -> None:
    """Close exactly the Appium session created for one flow."""

    driver.quit()
