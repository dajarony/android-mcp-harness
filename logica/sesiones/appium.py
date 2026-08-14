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
from contratos.mcp import HarnessError, McpErrorCode
from logica.infraestructura.appium import read_appium_status
from logica.infraestructura.lanzador import start_settings_apps
from logica.seguridad.emulador import assert_emulator_udid, assert_local_appium_url


def create_settings_driver(config: SettingsDemoConfig) -> Any:
    """Connect one Appium session and bring Android Settings to foreground."""

    driver = create_device_driver(config)
    start_settings_apps(config.udid)
    return driver


def create_device_driver(config: SettingsDemoConfig) -> Any:
    """Connect one transient session without choosing or launching an Android app."""

    # Every session-opening tool funnels through here, so both boundaries are
    # checked before a request can leave: a physical UDID or a remote Appium
    # would otherwise reach the network and take the harness off the emulator.
    assert_emulator_udid(config.udid)
    assert_local_appium_url(config.appium_url)
    # A stopped Appium is a declared, recoverable condition. Asking its status
    # first costs one local request and keeps the client from receiving
    # INTERNAL_ERROR when the FASER promises APPIUM_UNAVAILABLE.
    read_appium_status(config.appium_url)
    try:
        return _connect(config, _base_options(config))
    except TimeoutError as exc:
        # Running out of time is a declared, recoverable condition. Letting it
        # fall through to the generic handler told the client INTERNAL_ERROR and
        # hid the one fact that would have explained it.
        raise HarnessError(
            McpErrorCode.OPERATION_TIMEOUT,
            "Android did not finish opening an Appium session within "
            f"{config.connect_timeout_seconds} s. A cold device installs a server "
            "app first; raise ANDROID_MCP_CONNECT_TIMEOUT on slow hardware.",
        ) from exc


def _base_options(config: SettingsDemoConfig) -> UiAutomator2Options:
    """Build shared emulator-only Appium capabilities."""

    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.automation_name = "UiAutomator2"
    options.device_name = "Android Emulator"
    options.udid = config.udid
    options.no_reset = True
    options.new_command_timeout = 60
    return options


def _connect(config: SettingsDemoConfig, options: UiAutomator2Options) -> Any:
    """Create the Appium client with the project-wide connection budget."""

    client_config = AppiumClientConfig(
        remote_server_addr=config.appium_url,
        timeout=config.connect_timeout_seconds,
        direct_connection=False,
    )
    return webdriver.Remote(options=options, client_config=client_config)


def close_driver(driver: Any) -> None:
    """Close exactly the Appium session created for one flow."""

    driver.quit()
