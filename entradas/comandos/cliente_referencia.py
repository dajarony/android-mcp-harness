"""
SUME DOCBLOCK

Nombre: cliente_referencia
Tipo: Entrada

Entradas:
- Ruta a un flujo JSON declarado y servidor MCP local por stdio.

Acciones:
- Lanza el servidor como proceso hijo, ejecuta el cliente de referencia y reporta JSON.

Salidas:
- Código de proceso y ReferenceRun serializado en la terminal.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from contratos.cliente_referencia import parse_reference_flow
from logica.servicios.cliente_referencia.runner import run_reference_flow
from salidas.consola.cliente_referencia import render_reference_run


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a declared Android task through the local MCP server."
    )
    parser.add_argument("flow", type=Path, help="JSON file with package_name and semantic steps.")
    return parser.parse_args()


def _structured_payload(result: object) -> dict[str, Any]:
    payload = result.model_dump(by_alias=True)
    structured = payload["structuredContent"]
    if not isinstance(structured, dict):
        raise RuntimeError("MCP server returned no structured result.")
    return structured


async def _run(flow_path: Path) -> int:
    raw = json.loads(flow_path.read_text(encoding="utf-8"))
    flow = parse_reference_flow(raw)
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "entradas.mcp.server"],
        cwd=str(PROJECT_ROOT),
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
    )
    async with stdio_client(server) as (read, write):
        # The stdio transport exposes reader/writer streams, not a high-level
        # in-memory Client.  ClientSession owns this transport and must be
        # initialized before tools can be called.
        async with ClientSession(read, write) as client:
            await client.initialize()

            async def call(tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
                return _structured_payload(await client.call_tool(tool, arguments))

            run = await run_reference_flow(call, flow)
    print(render_reference_run(run))
    return 0 if run.ok else 1


def main() -> int:
    """Read one declared flow and return its truthful process status."""

    return asyncio.run(_run(_arguments().flow))


if __name__ == "__main__":
    raise SystemExit(main())
