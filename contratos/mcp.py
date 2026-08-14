"""
SUME DOCBLOCK

Nombre: mcp
Tipo: Contrato

Entradas:
- Nombre de herramienta, datos de resultado, evidencia y errores tipados.

Acciones:
- Define la forma pública y estable de respuestas del servidor MCP.

Salidas:
- Códigos de error, excepción tipada y respuestas serializables.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any
from uuid import uuid4


class McpErrorCode(StrEnum):
    """Expected errors declared by the MCP FASER."""

    EMULATOR_UNAVAILABLE = "EMULATOR_UNAVAILABLE"
    APPIUM_UNAVAILABLE = "APPIUM_UNAVAILABLE"
    EMULATOR_BUSY = "EMULATOR_BUSY"
    SETTINGS_FOREGROUND_FAILED = "SETTINGS_FOREGROUND_FAILED"
    UI_ELEMENT_NOT_FOUND = "UI_ELEMENT_NOT_FOUND"
    UI_TREE_UNAVAILABLE = "UI_TREE_UNAVAILABLE"
    OPERATION_TIMEOUT = "OPERATION_TIMEOUT"
    EVIDENCE_WRITE_FAILED = "EVIDENCE_WRITE_FAILED"
    INVALID_PACKAGE = "INVALID_PACKAGE"
    APP_NOT_FOUND = "APP_NOT_FOUND"
    INVALID_SELECTOR = "INVALID_SELECTOR"
    INVALID_TEXT = "INVALID_TEXT"
    INVALID_SCROLL_DIRECTION = "INVALID_SCROLL_DIRECTION"
    INVALID_UI_SESSION = "INVALID_UI_SESSION"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class HarnessError(Exception):
    """Expected operational failure that can be safely exposed to an MCP client."""

    def __init__(
        self,
        code: McpErrorCode,
        message: str,
        evidence: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.evidence = evidence


@dataclass(frozen=True)
class McpError:
    """Public error payload without host stack traces."""

    code: str
    message: str


@dataclass(frozen=True)
class McpToolResult:
    """Normalized output returned by every custom MCP tool."""

    ok: bool
    operation_id: str
    tool: str
    data: dict[str, Any]
    evidence: dict[str, str] | None
    error: McpError | None

    @classmethod
    def success(
        cls,
        tool: str,
        data: dict[str, Any],
        evidence: dict[str, str] | None = None,
    ) -> "McpToolResult":
        """Create one successful normalized response."""

        return cls(True, str(uuid4()), tool, data, evidence, None)

    @classmethod
    def failure(
        cls,
        tool: str,
        error: HarnessError,
        evidence: dict[str, str] | None = None,
    ) -> "McpToolResult":
        """Create one failed normalized response."""

        return cls(
            False,
            str(uuid4()),
            tool,
            {},
            evidence,
            McpError(error.code.value, error.message),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the contract into MCP structured output."""

        return asdict(self)
