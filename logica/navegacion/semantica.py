"""
SUME DOCBLOCK

Nombre: semantica
Tipo: Lógica

Entradas:
- Driver Appium, SemanticSelector, texto validado o dirección validada.

Acciones:
- Resuelve elementos por semántica y realiza una única acción Android.

Salidas:
- Descripción observable de la acción o HarnessError tipado.
"""

from __future__ import annotations

from typing import Any

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait

from contratos.mcp import HarnessError, McpErrorCode
from contratos.ui_control import SemanticSelector
from logica.navegacion.resumen import summarize_ui_tree


def _xpath_literal(value: str) -> str:
    """Quote untrusted text as an XPath literal instead of interpolating code."""

    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'
    segments = value.split("'")
    quoted = [f"'{segment}'" for segment in segments]
    return "concat(" + ', "\'", '.join(quoted) + ")"


def _locator(selector: SemanticSelector) -> tuple[str, str]:
    """Translate one validated selector into an Appium locator pair."""

    if selector.kind == "resource_id":
        return AppiumBy.ID, selector.value
    if selector.kind == "content_desc":
        return AppiumBy.ACCESSIBILITY_ID, selector.value
    literal = _xpath_literal(selector.value)
    if selector.kind == "text":
        return AppiumBy.XPATH, f"//*[@text={literal}]"
    if selector.kind == "input_hint":
        # Two rules, both learned the hard way from a real screen.
        #
        # The class is matched by suffix, not by equality: Android's search field
        # is a plain EditText on one release and an AppCompatEditText on another.
        # XPath 1.0 has no ends-with, so the last eight characters are compared.
        #
        # The hint is looked for in the same four places the screen summary looks,
        # descendants included, and by text as well as description. When these two
        # disagree the summary offers a target the locator cannot then find, which
        # is the worst failure this harness can produce: it advertises a door and
        # then says the door is not there.
        editable = "substring(@class, string-length(@class) - 7) = 'EditText'"
        return (
            AppiumBy.XPATH,
            f"//*[{editable} and ("
            f"contains(@hint, {literal})"
            f" or contains(@content-desc, {literal})"
            f" or contains(@text, {literal})"
            f" or .//*[contains(@content-desc, {literal})"
            f" or contains(@text, {literal})])]",
        )
    return AppiumBy.XPATH, f"//*[contains(@text, {literal})]"


def _offered_instead(driver: Any) -> str:
    """Name what the screen does offer, so 'not found' is actionable.

    A caller told only that nothing matched has to guess blindly at its next
    move. Telling it what is actually reachable turns a dead end into a retry,
    and it is the difference between debugging a run and staring at it.
    """

    try:
        summary = summarize_ui_tree(driver.page_source)
    except Exception:  # noqa: BLE001 - a diagnostic must never mask the real error
        return ""
    # The role travels with the label: knowing a target is an input rather than a
    # button is what tells a caller whether to tap it or type into it.
    labels = [
        f"{action['label'][:40]!r} ({action['role']})"
        for action in summary["actions"]
        if action["label"]
    ]
    if not labels:
        return ""
    shown = ", ".join(labels[:10])
    more = f" and {len(labels) - 10} more" if len(labels) > 10 else ""
    return f" The screen offers: {shown}{more}."


def find_element(driver: Any, selector: SemanticSelector) -> Any:
    """Wait for exactly the declared semantic target, never a coordinate fallback."""

    by, query = _locator(selector)
    try:
        return WebDriverWait(driver, 10).until(
            lambda active: active.find_element(by, query)
        )
    except TimeoutException as exc:
        raise HarnessError(
            McpErrorCode.UI_ELEMENT_NOT_FOUND,
            f"No visible element matched {selector.kind!r} before timeout."
            + _offered_instead(driver),
        ) from exc


def tap(driver: Any, selector: SemanticSelector) -> str:
    """Tap one semantic element and return the most useful visible label."""

    element = find_element(driver, selector)
    label = _element_label(element, selector)
    try:
        element.click()
    except WebDriverException as exc:
        raise HarnessError(
            McpErrorCode.UI_ELEMENT_NOT_FOUND,
            "The semantic element was found but could not be tapped.",
        ) from exc
    return label


def type_text(driver: Any, selector: SemanticSelector, text: str) -> int:
    """Send validated text to one semantic input without clearing existing content."""

    element = find_element(driver, selector)
    try:
        element.send_keys(text)
    except WebDriverException as exc:
        raise HarnessError(
            McpErrorCode.UI_ELEMENT_NOT_FOUND,
            "The semantic element was found but could not receive text.",
        ) from exc
    return len(text)


def scroll(driver: Any, direction: str) -> None:
    """Perform one trusted normalized vertical gesture; no coordinates enter MCP."""

    size = driver.get_window_size()
    center_x = size["width"] // 2
    upper_y = int(size["height"] * 0.25)
    lower_y = int(size["height"] * 0.75)
    start_y, end_y = (lower_y, upper_y) if direction == "down" else (upper_y, lower_y)
    try:
        driver.swipe(center_x, start_y, center_x, end_y, duration=300)
    except WebDriverException as exc:
        raise HarnessError(
            McpErrorCode.OPERATION_TIMEOUT,
            "Android did not complete the normalized scroll gesture.",
        ) from exc


def go_back(driver: Any) -> str:
    """Execute Android Back and report the package visible afterwards."""

    try:
        driver.back()
        return str(driver.current_package)
    except WebDriverException as exc:
        raise HarnessError(
            McpErrorCode.OPERATION_TIMEOUT,
            "Android did not complete the Back navigation.",
        ) from exc


def _element_label(element: Any, selector: SemanticSelector) -> str:
    """Describe a tapped element without returning the driver element itself."""

    return (
        element.get_attribute("text")
        or element.get_attribute("contentDescription")
        or selector.value
    )
