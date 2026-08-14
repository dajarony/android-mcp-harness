"""
SUME DOCBLOCK

Nombre: cliente_referencia
Tipo: Contrato

Entradas:
- Especificación declarativa de una campaña MCP y respuestas estructuradas.

Acciones:
- Define pasos permitidos y el informe serializable de una campaña de referencia.

Salidas:
- ReferenceFlow y ReferenceRun sin dependencias de transporte MCP.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from contratos.mcp import HarnessError, McpErrorCode
from contratos.ui_control import validate_package_name


_UI_TOOLS = frozenset({"ui.tap", "ui.type_text", "ui.scroll", "device.back"})


@dataclass(frozen=True)
class ReferenceStep:
    """One explicitly approved client action, without a caller-controlled session."""

    tool: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ReferenceFlow:
    """A package and the semantic actions the reference client may perform."""

    package_name: str
    steps: tuple[ReferenceStep, ...]


@dataclass(frozen=True)
class ReferenceRun:
    """Portable report of the observations, actions and evidence of one campaign."""

    ok: bool
    package_name: str
    initial_tree: dict[str, Any] | None
    actions: tuple[dict[str, Any], ...]
    final_tree: dict[str, Any] | None
    session_closed: bool
    error: dict[str, str] | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_reference_flow(raw: object) -> ReferenceFlow:
    """Accept only a small declarative vocabulary; the server owns all authority."""

    if not isinstance(raw, dict) or set(raw) != {"package_name", "steps"}:
        raise HarnessError(
            McpErrorCode.INVALID_PACKAGE,
            "reference flow must contain exactly package_name and steps.",
        )
    package_name = validate_package_name(raw["package_name"])
    raw_steps = raw["steps"]
    if not isinstance(raw_steps, list) or not raw_steps:
        raise HarnessError(
            McpErrorCode.INVALID_SELECTOR,
            "reference flow steps must be a nonempty list.",
        )

    steps: list[ReferenceStep] = []
    for raw_step in raw_steps:
        if not isinstance(raw_step, dict) or set(raw_step) != {"tool", "arguments"}:
            raise HarnessError(
                McpErrorCode.INVALID_SELECTOR,
                "each reference step must contain exactly tool and arguments.",
            )
        tool = raw_step["tool"]
        arguments = raw_step["arguments"]
        if not isinstance(tool, str) or tool not in _UI_TOOLS or not isinstance(arguments, dict):
            raise HarnessError(
                McpErrorCode.INVALID_SELECTOR,
                "reference steps may call only ui.tap, ui.type_text, ui.scroll or device.back.",
            )
        if "session_id" in arguments:
            raise HarnessError(
                McpErrorCode.INVALID_SELECTOR,
                "reference flow must not provide session_id; the client owns that lease.",
            )
        steps.append(ReferenceStep(tool, arguments))
    return ReferenceFlow(package_name, tuple(steps))
