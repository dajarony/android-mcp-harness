# Android MCP Server Module

## Purpose

Exponer solo las cuatro herramientas MCP autorizadas para observar y navegar el
emulador Android local.

## Lifecycle

- **init:** `build_server()` crea el catálogo MCP y el controlador.
- **run:** `main()` sirve por stdio; no abre HTTP ni lanza procesos.
- **fallback:** toda herramienta devuelve el contrato `McpToolResult` con un
  código tipado y nunca un stacktrace.
- **checkHealth:** `emulator.get_status` consulta ADB y Appium.
- **shutdown:** el SDK MCP cierra stdio; cada navegación cierra su sesión Appium.

## Dependencies

- SDK oficial `mcp`: protocolo stdio y catálogo de herramientas.
- `AndroidMcpController`: coordinación de las acciones permitidas.
- Adaptadores ADB/Appium: lectura local y navegación limitada.

## State owned

- `EmulatorOperationGate._lock`: exclusividad de una operación sobre el
  emulador compartido.
- No guarda sesión Appium entre llamadas ni estado de UI persistente.

## Events

### Emits

- Respuesta MCP normalizada de cada llamada, con `operation_id`.

### Listens

- Solicitudes MCP `tools/list` y `tools/call` del transporte stdio.

## Errors

| Code | Fallback |
|---|---|
| `EMULATOR_UNAVAILABLE` | No llamar Appium; pedir iniciar el AVD. |
| `APPIUM_UNAVAILABLE` | No lanzar Appium; pedir al operador iniciarlo. |
| `EMULATOR_BUSY` | Rechazar sin cola; cliente reintenta. |
| `UI_ELEMENT_NOT_FOUND` | Capturar evidencia; no usar coordenadas. |
| `INTERNAL_ERROR` | Cerrar recursos y devolver mensaje seguro. |

## Tests

- Catálogo MCP contiene exactamente las cuatro herramientas personalizadas.
- Cada respuesta cumple el contrato común.
- El bloqueo rechaza una segunda operación concurrente.
- ECA verifica efectos de las herramientas contra el emulador real.
