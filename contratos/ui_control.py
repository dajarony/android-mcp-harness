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


_PACKAGE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+$")
_SELECTOR_KEYS = {
    "resource_id",
    "text",
    "content_desc",
    "text_contains",
    "input_hint",
}


@dataclass(frozen=True)
class SemanticSelector:
    """One resolved semantic locator; mixed locators are intentionally forbidden."""

    kind: str
    value: str


def validate_package_name(package_name: object) -> str:
    """Accept only Android package syntax, never shell-like input."""

    if not isinstance(package_name, str) or not _PACKAGE_NAME.fullmatch(package_name):
        raise HarnessError(
            McpErrorCode.INVALID_PACKAGE,
            "package_name must be a valid Android package identifier.",
        )
    return package_name


def validate_selector(raw_selector: object) -> SemanticSelector:
    """Require exactly one nonempty approved semantic selector."""

    if not isinstance(raw_selector, dict):
        raise HarnessError(
            McpErrorCode.INVALID_SELECTOR,
            "selector must be an object with exactly one supported semantic key.",
        )
    keys = set(raw_selector)
    if not keys.issubset(_SELECTOR_KEYS) or len(keys) != 1:
        raise HarnessError(
            McpErrorCode.INVALID_SELECTOR,
            "selector must contain exactly one of resource_id, text, content_desc, text_contains or input_hint.",
        )
    kind = next(iter(keys))
    value = raw_selector[kind]
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > 256
        or "\x00" in value
    ):
        raise HarnessError(
            McpErrorCode.INVALID_SELECTOR,
            "selector value must be nonempty, at most 256 characters and contain no NUL.",
        )
    return SemanticSelector(kind, value)


def validate_text(text: object) -> str:
    """Bound text input before it reaches a UI field."""

    if not isinstance(text, str) or not text or len(text) > 512 or "\x00" in text:
        raise HarnessError(
            McpErrorCode.INVALID_TEXT,
            "text must contain 1 to 512 characters and no NUL.",
        )
    return text


def validate_scroll_direction(direction: object) -> str:
    """Accept only the two declared scroll intentions."""

    if direction not in {"up", "down"}:
        raise HarnessError(
            McpErrorCode.INVALID_SCROLL_DIRECTION,
            "direction must be exactly 'up' or 'down'.",
        )
    return str(direction)


def selector_mapping(selector: SemanticSelector) -> dict[str, Any]:
    """Expose one normalized selector in result data without leaking driver objects."""

    return {selector.kind: selector.value}
