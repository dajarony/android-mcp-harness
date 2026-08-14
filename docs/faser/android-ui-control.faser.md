===============================================================
Componente: Android UI Control Module
Tipo: Service / MCP Gateway extension
Version: 0.4.0
===============================================================

> Extiende [`mcp-server.faser.md`](mcp-server.faser.md), que define la frontera
> común: catálogo, contrato de salida, exclusividad y evidencia. Las seis
> herramientas de aquí viven en ese mismo proceso y bajo ese mismo bloqueo.

## DEFINICIÓN

**Descripción:** amplía el servidor MCP local con acciones semánticas sobre un
único Android emulado. Cada llamada hace una sola cosa y devuelve evidencia.

**Objetivo medible:** 100% de las acciones declaradas responden en ≤30 s con
resultado tipado, no dejan sesión Appium activa y nunca aceptan coordenadas,
shell ni un UDID físico.

## ESTADO

| Estado | Tipo / inicial | Propietario | Regla |
|---|---|---|---|
| `activeOperation` | `bool`, `false` | `EmulatorOperationGate` | Solo una llamada sobre el emulador. |
| `operationId` | UUID nuevo | `McpToolResult` | No reutilizable. |
| `driver` | temporal / `null` | sesión Appium | Se cierra en `finally`. |
| `evidencePath` | `str / null` | evidencia | Único y bajo `artifacts/`. |

## ENTRADAS

- `app.list_installed`: sin argumentos.
- `app.open(package_name: str)`.
- `ui.tap(selector: object)`.
- `ui.type_text(selector: object, text: str)`.
- `ui.scroll(direction: "up" | "down")`.
- `device.back`: sin argumentos.

`selector` contiene exactamente una de estas formas:

```json
{"resource_id": "android:id/button1"}
{"text": "Allow"}
{"content_desc": "Navigate up"}
{"text_contains": "Settings"}
{"input_hint": "Search"}
```

## EVENTOS

### Evento: `app.list_installed`

**Condición:** UDID de emulador válido.

**Acción:** ejecutar únicamente `adb shell pm list packages`, ya fijado por el
adaptador de lectura.

**Resultado:** lista de paquetes, sin sesión Appium ni cambio de UI.

**Error:** `EMULATOR_UNAVAILABLE`.

### Evento: `app.open`

**Condición:** nombre de paquete válido y gate libre.

**Acción:** resolver la actividad Android `MAIN/LAUNCHER` del paquete mediante
una consulta fija, iniciar exactamente ese componente, comprobar el árbol UI y
capturar evidencia. No se acepta un componente aportado por MCP.

**Resultado:** `foreground_package == package_name` para un paquete lanzable.

**Error:** `INVALID_PACKAGE`, `APP_NOT_FOUND`, `OPERATION_TIMEOUT`.

### Evento: `ui.tap`

**Condición:** selector semántico exacto y gate libre.

**Acción:** abrir sesión, localizar un único elemento durante ≤10 s, pulsarlo,
capturar y cerrar.

**Resultado:** texto/etiqueta del elemento y paquete foreground posterior.

**Error:** `INVALID_SELECTOR`, `UI_ELEMENT_NOT_FOUND`, `OPERATION_TIMEOUT`.

### Evento: `ui.type_text`

**Condición:** selector exacto y texto válido.

**Acción:** localizar campo, enviar texto, capturar y cerrar.

**Resultado:** número de caracteres enviado y paquete foreground.

**Error:** `INVALID_TEXT`, `INVALID_SELECTOR`, `UI_ELEMENT_NOT_FOUND`.

### Evento: `ui.scroll`

**Condición:** dirección `up` o `down`.

**Acción:** ejecutar un gesto interno normalizado sobre la ventana actual;
ninguna coordenada entra desde MCP. Capturar y cerrar.

**Resultado:** dirección realizada y paquete foreground.

**Error:** `INVALID_SCROLL_DIRECTION`, `OPERATION_TIMEOUT`.

### Evento: `device.back`

**Condición:** gate libre.

**Acción:** enviar Back por Appium, devolver paquete foreground, capturar y
cerrar.

**Resultado:** navegación atrás observable.

**Error:** `OPERATION_TIMEOUT` o `INTERNAL_ERROR`.

## VALIDACIONES

- `package_name` cumple la sintaxis Android; no es un comando.
- Selector: una sola clave permitida, valor no vacío ≤256 caracteres y sin NUL.
- Texto: 1–512 caracteres, sin NUL.
- Dirección: exactamente `up` o `down`.
- Una acción siempre se serializa mediante el gate.
- Cada acción obtiene evidencia propia y cierra driver aunque falle.
- Ninguna herramienta recibe ni ejecuta ADB shell arbitrario.
- El UDID y el punto final de Appium se validan en el creador de sesión, embudo
  común de las seis acciones: un teléfono físico o un Appium remoto se rechazan
  antes de que salga la petición, no después.

## ERRORES Y FALLBACK

| Código | Fallback |
|---|---|
| `INVALID_PACKAGE` | Rechazar antes de crear sesión. |
| `APP_NOT_FOUND` | Devolver error tipado y evidencia si hubo sesión. |
| `INVALID_SELECTOR` | Rechazar antes de crear sesión. |
| `INVALID_TEXT` | Rechazar antes de crear sesión. |
| `INVALID_SCROLL_DIRECTION` | Rechazar antes de crear sesión. |
| `UI_ELEMENT_NOT_FOUND` | Capturar pantalla y no usar coordenadas alternativas. |
| `EMULATOR_BUSY` | Rechazo inmediato; el cliente puede reintentar. |

## PRUEBAS Y ECA

- Abrir `com.example.myapplication` termina en ese paquete y muestra su árbol.
- Selector por `text` y por `text_contains` con la misma intención llegan al
  mismo elemento cuando son equivalentes.
- Selector con dos claves, vacío, desconocido o NUL se rechaza antes de Appium.
- Dos acciones concurrentes: una se ejecuta, otra recibe `EMULATOR_BUSY`.
- Dos acciones consecutivas conservan dos capturas distintas.
- Un paquete inexistente devuelve `APP_NOT_FOUND`, no `ok=true`.
- Tras cada éxito o error, una operación posterior puede adquirir el gate.
- Con un UDID de teléfono físico, las seis acciones responden
  `EMULATOR_UNAVAILABLE` y un Appium espía recibe cero peticiones.

## DECISIONES

- Se elige MCP stdio y el AVD desechable como frontera de control.
- Se elige acción semántica, no coordenadas proporcionadas por el modelo.
- Se elige validar la configuración en el creador de sesión y no en cada
  herramienta: un embudo único no se olvida cuando se añade la herramienta once.
- Se pospone cámara, permisos y teléfono físico hasta tener un contrato propio.

## ACLARACIÓN IMPLEMENTADA (Android 16)

- `selector` permite exactamente una de `resource_id`, `text`, `content_desc`,
  `text_contains` o `input_hint`; este último localiza un campo `EditText` sin
  XPath proporcionado por MCP. Busca la pista en los cuatro sitios donde Android
  la guarda según versión y kit de interfaz: `hint`, `content-desc` y `text`
  propios, y `content-desc` de un descendiente, que es la forma de Compose.
  Limitarse a la última ataba el selector a una versión de Android, que es justo
  lo que vino a evitar. Una vez escrito, el `text` deja de ser la pista: este
  selector sirve para encontrar el campo, no para volver a él con contenido.
- `settings.open_apps` usa la intención Android fija
  `android.settings.APPLICATION_SETTINGS` y confirma el marcador observable
  `All apps`.
- `ui.tap` obtiene la etiqueta antes de tocar: si la pantalla cambia, una acción
  realmente aplicada no se convierte en un falso error por un elemento stale.
