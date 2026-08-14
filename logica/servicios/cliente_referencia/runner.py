"""
SUME DOCBLOCK

Nombre: runner
Tipo: Lógica

Entradas:
- ReferenceFlow y una función que invoca herramientas MCP por stdio.

Acciones:
- Ejecuta abrir, observar, encadenar acciones declaradas y cerrar la sesión.

Salidas:
- ReferenceRun con resultados estructurados y evidencia de cada acción.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from contratos.cliente_referencia import ReferenceFlow, ReferenceRun


ToolCall = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


def _error(payload: dict[str, Any] | None) -> dict[str, str] | None:
    if payload is None:
        return None
    error = payload.get("error")
    return error if isinstance(error, dict) else None


async def run_reference_flow(call: ToolCall, flow: ReferenceFlow) -> ReferenceRun:
    """Run an explicit task through MCP without interpreting raw Android XML."""

    opened = await call("app.open", {"package_name": flow.package_name})
    if not opened.get("ok"):
        return ReferenceRun(False, flow.package_name, None, (opened,), None, False, _error(opened))

    initial_tree = await call("ui.get_tree", {})
    if not initial_tree.get("ok"):
        return ReferenceRun(
            False, flow.package_name, initial_tree, (opened,), None, False, _error(initial_tree)
        )

    session = await call("ui.session.open", {})
    if not session.get("ok"):
        return ReferenceRun(
            False, flow.package_name, initial_tree, (opened, session), None, False, _error(session)
        )
    session_data = session.get("data")
    session_id = session_data.get("session_id") if isinstance(session_data, dict) else None
    if not isinstance(session_id, str):
        return ReferenceRun(
            False,
            flow.package_name,
            initial_tree,
            (opened, session),
            None,
            False,
            {"code": "MCP_PROTOCOL_ERROR", "message": "ui.session.open returned no session_id."},
        )

    actions: list[dict[str, Any]] = [opened, session]
    failure: dict[str, str] | None = None
    try:
        for step in flow.steps:
            arguments = {**step.arguments, "session_id": session_id}
            result = await call(step.tool, arguments)
            actions.append(result)
            if not result.get("ok"):
                failure = _error(result)
                break
    finally:
        closed = await call("ui.session.close", {"session_id": session_id})
        actions.append(closed)
        if not closed.get("ok") and failure is None:
            failure = _error(closed)

    final_tree = await call("ui.get_tree", {})
    if not final_tree.get("ok") and failure is None:
        failure = _error(final_tree)
    return ReferenceRun(
        failure is None,
        flow.package_name,
        initial_tree,
        tuple(actions),
        final_tree,
        bool(closed.get("ok")),
        failure,
    )
