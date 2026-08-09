"""Phase-1 smoke test: Settings -> Apps on an Android emulator only."""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
APPIUM_URL = os.getenv("APPIUM_URL", "http://127.0.0.1:4723")
UDID = os.getenv("ANDROID_UDID", "emulator-5554")


def screenshot_path(label: str) -> Path:
    ARTIFACTS.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return ARTIFACTS / f"{stamp}-{label}.png"


def main() -> int:
    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.automation_name = "UiAutomator2"
    options.device_name = "Android Emulator"
    options.udid = UDID
    options.app_package = "com.android.settings"
    options.app_activity = ".Settings"
    options.no_reset = True
    # Keep emulator data intact but always bring Settings to the foreground.
    # Without this, an existing Settings process can leave the session on the
    # launcher and make UI assertions test the wrong application.
    options.set_capability("appium:forceAppLaunch", True)
    options.new_command_timeout = 60

    driver = None
    try:
        print(f"Connecting to {APPIUM_URL} on {UDID}...")
        driver = webdriver.Remote(APPIUM_URL, options=options)
        if driver.current_package != "com.android.settings":
            raise RuntimeError(
                f"Expected Settings foreground package, got {driver.current_package!r}"
            )
        apps = WebDriverWait(driver, 20).until(
            lambda current: current.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiSelector().textContains("Apps")',
            )
        )
        print(f"Found Settings element: {apps.text!r}")
        apps.click()
        apps_screen_marker = WebDriverWait(driver, 10).until(
            lambda current: current.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiSelector().textContains("See all")',
            )
        )
        print(f"Reached Apps screen: {apps_screen_marker.text!r}")
        path = screenshot_path("settings-apps")
        driver.save_screenshot(str(path))
        print(f"PASS: Settings -> Apps; screenshot: {path}")
        return 0
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        if driver is not None:
            path = screenshot_path("failure")
            driver.save_screenshot(str(path))
            print(f"Failure screenshot: {path}", file=sys.stderr)
        return 1
    finally:
        if driver is not None:
            driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
