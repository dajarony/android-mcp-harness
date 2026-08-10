# CMCF — Control semántico del emulador Android

## 1. Intención Global

Permitir que un cliente MCP observe y recorra de forma reproducible el Android
desechable mediante intenciones semánticas, sin aceptar comandos ADB, rutas del
host ni coordenadas elegidas por el modelo.

## 2. Alcance

**Incluye:** listar paquetes instalados, abrir un paquete, pulsar por selector
semántico, escribir texto, scroll normalizado, volver atrás, leer árbol UI y
guardar evidencia.

**Excluye:** dispositivo físico, cámara, llamadas, SMS, contactos reales,
permisos administrativos, shell arbitraria, instalación/desinstalación de APK y
automatización del host Windows.

## 3. Bloques Principales

| BP | Propósito | Estado propio | Interfaz pública |
|---|---|---:|---|
| Contrato de intención | Validar paquete, selector, texto y dirección | No | `SemanticSelector`, validadores |
| Sesión de acción | Crear/cerrar una sesión Appium temporal | No persistente | `create_device_driver()` |
| Navegación semántica | Resolver elemento y ejecutar una única acción | No | `open_app`, `tap`, `type`, `scroll`, `back` |
| Observación | Listar paquetes y leer estado/UI | No | adaptador ADB y `ui.get_tree` |
| Orquestación MCP | Exclusividad, resultado tipado y evidencia | Bloqueo efímero | `AndroidMcpController` |
| Evidencia | Captura única posterior a cada acción | No | `save_screenshot()` |

## 4. UAFs

- `validate_package(name) -> str`: acepta solo nombre de paquete Android.
- `validate_selector(mapping) -> SemanticSelector`: exige exactamente un
  selector entre `resource_id`, `text`, `content_desc` o `text_contains`.
- `validate_text(value) -> str`: texto no vacío, sin NUL, máximo 512 caracteres.
- `validate_scroll_direction(value) -> str`: solo `up` o `down`.
- `list_installed_packages(udid) -> list[str]`: consulta ADB fija de lectura.
- `create_device_driver(config) -> Driver`: sesión temporal sin app fijada.
- `open_app(driver, package) -> str`: activa paquete y verifica foreground.
- `tap(driver, selector) -> str`: localiza semánticamente y pulsa un elemento.
- `type_text(driver, selector, text) -> str`: localiza un campo y escribe.
- `scroll(driver, direction) -> None`: gesto normalizado interno, sin coordenadas
  de entrada.
- `go_back(driver) -> str`: ejecuta Back y devuelve paquete visible.
- `save_screenshot(driver, label) -> Path`: evidencia única en `artifacts/`.

## 5. Flujo de Datos

`MCP tool call → contrato/validación → gate exclusivo → sesión Appium o ADB fijo
→ acción única → captura → McpToolResult → cliente MCP`.

## 6. Eventos

| Evento | Emisor | Consumidor | Carga |
|---|---|---|---|
| `tools/call` | Cliente MCP | Entrada MCP | nombre + argumentos |
| `operation.result` | Controlador MCP | Cliente MCP | resultado, evidencia, error tipado |

## 7. Decisiones y riesgos

- Se eligen selectores semánticos y no coordenadas externas para soportar cambios
  de resolución y auditar la intención.
- Se abre una sesión por acción para no dejar estado Appium huérfano.
- El emulador es desechable, pero el control sigue siendo acotado: no hay shell.
- Se rechaza “control completo” sobre teléfonos o host: no es el objetivo ni una
  frontera segura de este repositorio.

## 8. Siguiente artefacto

`docs/faser/android-ui-control.faser.md`, seguido de módulo y regresiones ECA.

## 9. Ajuste observado en Android 16

El `EditText` Compose de búsqueda no publica un `resource_id`. El contrato
incorpora `input_hint`, una intención semántica limitada que busca su etiqueta
de accesibilidad; no se acepta XPath ni coordenadas aportadas por el modelo.
