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

---

## 2026-08-10 — Regresión ECA de evidencia consecutiva

**Archivos afectados:**

- Actualizada `logica/evidencias/capturas.py`.
- Actualizados FASER, oráculo ECA y campaña del emulador.

**Motivo:**

- La campaña `SEQ-EVID-1` demostró que dos capturas dentro del mismo segundo
  compartían nombre y la segunda sobrescribía la evidencia de la primera.

**Impacto:**

- Las rutas añaden microsegundos; bajo el bloqueo de operación ya no colisionan
  en reintentos consecutivos.
- La regresión exige dos artefactos distintos y existentes antes de declarar
  verde la campaña.

**Autor:** Codex, con autorización del propietario.

---

## 2026-08-09 — FASER del servidor MCP local

**Archivos afectados:**

- Creado `docs/faser/mcp-server.faser.md`.
- Actualizado `mapa-global/arquitectura.yaml` con la especificación en estado
  `draft`.

**Motivo:**

- Declarar autoridad, estados, efectos, errores y pruebas ECA antes de escribir
  un servidor MCP que pueda controlar el emulador.

**Impacto:**

- No se añade código de ejecución ni se abre ninguna capacidad nueva.
- La futura implementación queda limitada a las cinco herramientas declaradas.

**Autor:** Codex, con autorización del propietario.

---

## 2026-08-10 — Servidor MCP local y campaña ECA del emulador

**Archivos afectados:**

- Añadidos `entradas/mcp/`, `contratos/mcp.py`, adaptadores ADB/Appium,
  frontera de seguridad y controlador MCP.
- Añadidos contrato de ciclo de vida y oráculo `docs/eca/mcp-emulator-v1.md`.
- Actualizados FASER, mapa global, requisitos y README.
- Añadidas regresiones unitarias y campaña opcional contra el emulador real.

**Motivo:**

- Exponer una frontera MCP local, mínima y trazable para que un cliente futuro
  pueda observar y navegar el AVD sin recibir ADB arbitrario ni red adicional.

**Impacto:**

- El servidor ofrece cuatro herramientas personalizadas por stdio.
- Las lecturas usan comandos ADB fijos y no crean sesiones Appium; solo
  `settings.open_apps` puede cambiar la UI del emulador.
- La campaña ECA real verificó 3/3 invariantes: observación sin navegación,
  navegación con evidencia y protocolo stdio en proceso independiente.

**Autor:** Codex, con autorización del propietario.

---

## 2026-08-10 — Control semántico Android verificado por ECA

**Archivos afectados:**

- Añadidos `contratos/ui_control.py`, lanzador Android y navegación semántica.
- Ampliado MCP con listado de paquetes, apertura de app, toque, texto,
  desplazamiento y volver.
- Actualizados CMCF, FASER, mapa SUME y campaña ECA real.

**Motivo:**

- Permitir a un cliente MCP controlar el AVD mediante intenciones auditables,
  sin coordenadas de entrada ni shell arbitraria.

**Hallazgos ECA y correcciones:**

- Android 16 restauraba una búsqueda previa de Settings; el flujo usa ahora la
  intención fija `android.settings.APPLICATION_SETTINGS`.
- Un toque que cambiaba de pantalla se reportaba como error al leer el elemento
  después de pulsarlo; la etiqueta se obtiene antes del toque.
- El `EditText` Compose no expone `resource-id`; se añadió el selector limitado
  `input_hint`, sin aceptar XPath ni coordenadas libres.

**Impacto:**

- Tres secuencias ECA reales confirman Apps, toque/desplazamiento/volver y
  búsqueda/escritura con evidencia propia.
- El alcance sigue limitado al AVD configurado; no controla host ni teléfonos
  físicos.

**Autor:** Codex, con autorización del propietario.
