"""
SUME DOCBLOCK

Nombre: ui_control
Tipo: Contrato

Entradas:
- Paquete Android, selector semántico, texto y dirección de scroll MCP.

Acciones:
- Valida las intenciones de control antes de crear una sesión Appium.

Salidas:
- Valores normalizados o HarnessError tipado y seguro.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from contratos.mcp import HarnessError, McpErrorCode


# Android allows a single-segment package such as "android"; requiring a dot
# rejected real packages that app.list_installed had just offered.
_PACKAGE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)*$")
# Control characters are not text on Android: a newline in an EditText fires the
# IME action, and a bidi override makes evidence read differently from what ran.
_BIDI_OVERRIDES = frozenset("‪‫‬‭‮⁦⁧⁨⁩")
_SELECTOR_KEYS = {
    "resource_id",
    "text",
    "content_desc",
    "text_contains",
    "input_hint",
}


@dataclass(frozen=True)
class SemanticSelector:
    """One semantic target, optionally narrowed by one semantic ancestor."""

    kind: str
    value: str
    within: "SemanticSelector | None" = None


def carries_control_characters(value: str, *, allow_line_breaks: bool = False) -> bool:
    """Report text that would act on the device instead of being typed into it.

    Line breaks are an action inside a text field and plain content inside a
    label: Flutter merges a widget's texts into one description joined by
    newlines, so `Historial\\nTab 2 of 3` is what the screen genuinely calls that
    tab. Refusing it in a selector made this harness unable to touch the tabs of
    a real app while its own summary was offering them.
    """

    allowed = {"\n", "\r", "\t"} if allow_line_breaks else set()
    return any(
        character not in allowed
        and (character < " " or character == "\x7f" or character in _BIDI_OVERRIDES)
        for character in value
    )


def validate_package_name(package_name: object) -> str:
    """Accept only Android package syntax, never shell-like input."""

    if not isinstance(package_name, str) or not _PACKAGE_NAME.fullmatch(package_name):
        raise HarnessError(
            McpErrorCode.INVALID_PACKAGE,
            "package_name must be a valid Android package identifier.",
        )
    return package_name


def validate_selector(raw_selector: object) -> SemanticSelector:
    """Validate a target and, at most, one semantic context that contains it."""

    return _validate_selector(raw_selector, allow_context=True)


def _validate_selector(
    raw_selector: object, *, allow_context: bool
) -> SemanticSelector:
    """Keep the public selector grammar finite: target plus one non-nested context."""

    if not isinstance(raw_selector, dict):
        raise HarnessError(
            McpErrorCode.INVALID_SELECTOR,
            "selector must be an object with one supported semantic key.",
        )
    keys = set(raw_selector)
    selector_keys = keys & _SELECTOR_KEYS
    allowed_keys = _SELECTOR_KEYS | ({"within"} if allow_context else set())
    if not keys.issubset(allowed_keys) or len(selector_keys) != 1:
        raise HarnessError(
            McpErrorCode.INVALID_SELECTOR,
            "selector must contain exactly one of resource_id, text, content_desc, "
            "text_contains or input_hint, plus optional within.",
        )
    kind = next(iter(selector_keys))
    value = raw_selector[kind]
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > 256
        or carries_control_characters(value, allow_line_breaks=True)
    ):
        raise HarnessError(
            McpErrorCode.INVALID_SELECTOR,
            "selector value must be nonempty, at most 256 characters and free of "
            "control characters other than line breaks and tabs.",
        )
    within = None
    if "within" in raw_selector:
        within = _validate_selector(raw_selector["within"], allow_context=False)
    return SemanticSelector(kind, value, within)


def validate_text(text: object) -> str:
    """Bound text input before it reaches a UI field."""

    if (
        not isinstance(text, str)
        or not text
        or len(text) > 512
        or carries_control_characters(text)
    ):
        raise HarnessError(
            McpErrorCode.INVALID_TEXT,
            "text must contain 1 to 512 characters and no control characters; "
            "a newline is an IME action, not text, and is not part of this tool.",
        )
    return text


def validate_scroll_direction(direction: object) -> str:
    """Accept one cardinal content movement, never caller-provided gesture data."""

    if direction not in {"up", "down", "left", "right"}:
        raise HarnessError(
            McpErrorCode.INVALID_SCROLL_DIRECTION,
            "direction must be exactly 'up', 'down', 'left' or 'right'.",
        )
    return str(direction)


def selector_mapping(selector: SemanticSelector) -> dict[str, Any]:
    """Expose one normalized selector in result data without leaking driver objects."""

    result: dict[str, Any] = {selector.kind: selector.value}
    if selector.within is not None:
        result["within"] = {selector.within.kind: selector.within.value}
    return result
