# Android MCP Server Module

## Purpose

Exponer solo las doce herramientas MCP autorizadas para observar y controlar el
emulador Android local: cuatro de observación (`emulator.get_status`,
`ui.get_tree`, `screen.capture`, `app.list_installed`), cinco de control
semántico (`app.open`, `ui.tap`, `ui.type_text`, `ui.scroll`, `device.back`),
la navegación declarada `settings.open_apps` y dos herramientas de flujo
explícito (`ui.session.open`, `ui.session.close`).

## Lifecycle

- **init:** `build_server()` crea el catálogo MCP y el controlador.
- **run:** `main()` sirve por stdio; no abre HTTP ni lanza procesos.
- **fallback:** toda herramienta devuelve el contrato `McpToolResult` con un
  código tipado y nunca un stacktrace.
- **checkHealth:** `emulator.get_status` consulta ADB y Appium.
- **shutdown:** el SDK MCP cierra stdio; las acciones sueltas cierran su driver
  en `finally` y los flujos explícitos caducan o se cierran por token.

## Dependencies

- SDK oficial `mcp`: protocolo stdio y catálogo de herramientas.
- `AndroidMcpController`: fachada de las herramientas, validación y coordinación.
- `UiActionExecutor`: ciclo de vida del driver, techo por acción y evidencia.
- `arbol`, `objetivos`, `maqueta` y `resumen`: lectura XML, selección semántica,
  auditoría visual y orquestación del resumen, respectivamente.
- Adaptadores ADB/Appium: lectura local y navegación limitada.

## State owned

- `EmulatorOperationGate._lock`: exclusividad de una operación sobre el
  emulador compartido.
- `UiFlowSessions._active`: como máximo un driver entre llamadas, solo cuando
  el cliente abrió un flujo explícito; caduca tras inactividad y no es estado
  de UI persistente.

## Events

### Emits

- Respuesta MCP normalizada de cada llamada, con `operation_id`.
- Recurso `artifact://{artifact_id}` con la evidencia PNG, para clientes que no
  comparten sistema de ficheros con el arnés.

### Listens

- Solicitudes MCP `tools/list` y `tools/call` del transporte stdio.

## Errors

| Code | Fallback |
|---|---|
| `EMULATOR_UNAVAILABLE` | No llamar Appium; pedir iniciar el AVD. |
| `APPIUM_UNAVAILABLE` | No lanzar Appium; pedir al operador iniciarlo. |
| `EMULATOR_BUSY` | Rechazar sin cola; cliente reintenta. |
| `INVALID_PACKAGE` / `INVALID_SELECTOR` / `INVALID_TEXT` / `INVALID_SCROLL_DIRECTION` | Rechazar antes de crear sesión. |
| `APP_NOT_FOUND` | Error tipado y evidencia si hubo sesión. |
| `UI_ELEMENT_NOT_FOUND` | Capturar evidencia; no usar coordenadas. |
| `OPERATION_TIMEOUT` | Abandonar la espera, invalidar el flujo si lo había y liberar el gate. |
| `UI_TREE_UNAVAILABLE` / `EVIDENCE_WRITE_FAILED` | No afirmar éxito sin lectura ni prueba. |
| `INTERNAL_ERROR` | Cerrar recursos y devolver mensaje seguro. |

## Tests

- Catálogo MCP contiene exactamente las doce herramientas personalizadas.
- Cada respuesta cumple el contrato común.
- El bloqueo rechaza una segunda operación concurrente.
- Ninguna herramienta que abre sesión acepta un UDID físico ni un Appium fuera
  de loopback; un Appium espía recibe cero peticiones.
- ECA verifica efectos, cadena de flujo y ausencia de sesiones huérfanas contra
  el emulador real.
