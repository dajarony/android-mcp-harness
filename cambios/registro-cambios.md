# Registro de Cambios — android-mcp-harness

> **Append-only.** Las entradas antiguas no se reescriben.

---

## 2026-08-09 — Arquitectura SUME + STDG instalada

**Archivos afectados:**

- Creada la estructura `entradas/`, `logica/`, `salidas/`, `contratos/`,
  `cambios/` y `mapa-global/`.
- Creado `mapa-global/arquitectura.yaml`, `.sume`, `SUME-README.md` y CMCF.
- Repartida la demostración Appium entre entrada, lógica, contrato y salida.
- Conservado `scripts/demo_settings.py` como entrada compatible.

**Motivo:**

- Separar responsabilidades, permitir crecimiento hacia MCP y conservar una
  trazabilidad legible por personas y agentes.

**Impacto:**

- La demostración conserva el mismo flujo funcional.
- Toda pieza futura debe tener una responsabilidad y actualizar el mapa y este
  registro.

**Autor:** Codex, con autorización del propietario.
