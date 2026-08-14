===============================================================
Componente: Android Emulator MCP Server
Tipo: Service / MCP Gateway
Version: 0.4.0
Estado: Implementado y verificado en emulador local
===============================================================

> **Alcance de este documento.** Aquí vive la frontera del servidor: catálogo,
> contrato común de salida, exclusividad, evidencia y las cuatro herramientas de
> observación más la navegación declarada `settings.open_apps`. Las seis
> herramientas de control semántico (`app.list_installed`, `app.open`, `ui.tap`,
> `ui.type_text`, `ui.scroll`, `device.back`) tienen su contrato propio en
> [`android-ui-control.faser.md`](android-ui-control.faser.md). El catálogo
> completo son **diez** herramientas y ninguna gana capacidades por estar
> descrita en un fichero u otro.

## DEFINICIÓN

**Descripción:** servidor MCP local por stdio que expone observación y
navegación verificable sobre un único emulador Android declarado. Delega la UI
a las capas SUME; no ejecuta ADB arbitrario ni controla el anfitrión.

**Objetivo medible:** cada llamada responde en ≤30 s con resultado normalizado;
las lecturas no mutan UI; toda navegación deja evidencia local de éxito o fallo.

**Contexto:** Trinidad u otro cliente MCP podrá usar las herramientas declaradas
contra un emulador desechable. Esta versión no abre puertos de red.

## ESTADO

| Estado | Tipo / valor inicial | Propietario | Regla |
|---|---|---|---|
| `configuredUdid` | `str`, `emulator-5554` | configuración de entrada | Debe empezar por `emulator-` y estar activo en ADB. |
| `operationId` | `UUID`, nuevo por llamada | controlador MCP | Nunca se reutiliza. |
| `activeOperation` | `bool`, `false` | gestor de sesión | Solo una operación UI por emulador. |
| `evidencePath` | `str \| null`, `null` | evidencia | Siempre bajo `artifacts/`. |

Los estados viven solo durante una operación salvo el archivo de evidencia. No
hay estado persistente de Appium ni sesiones compartidas entre llamadas.

## ENTRADAS

- `tools/list`: catálogo MCP sin parámetros.
- `emulator.get_status`: lectura de ADB y salud de Appium.
- `ui.get_tree`: lectura del árbol de accesibilidad/UI.
- `screen.capture`: captura local de la pantalla actual.
- `app.list_installed`: lectura de paquetes instalados.
- `settings.open_apps`: navegación declarada de Ajustes a Apps.

Definidas en [`android-ui-control.faser.md`](android-ui-control.faser.md) y
servidas por este mismo proceso, contrato y bloqueo:

- `app.open(package_name)`, `ui.tap(selector)`,
  `ui.type_text(selector, text)`, `ui.scroll(direction)`, `device.back`.

Configuración:

- `ANDROID_UDID` y `APPIUM_URL`: variables locales opcionales; sus valores por
  defecto son `emulator-5554` y `http://127.0.0.1:4723`. Ambas se validan antes
  de cualquier adaptador y antes de abrir sesión.

## CONTRATO COMÚN DE SALIDA

```json
{
  "ok": true,
  "operation_id": "uuid",
  "tool": "settings.open_apps",
  "data": {},
  "evidence": {"artifact_id": "...", "path": "artifacts/...png"},
  "error": null
}
```

En error, `ok` es `false`, `data` es `{}`, `error` contiene `code` y `message`,
y `evidence` contiene captura si la sesión alcanzó a abrirse. Nunca se expone un
stacktrace ni una ruta fuera de `artifacts/`.

## EVENTOS

### Evento: `tools/list`

**Condición:** servidor MCP iniciado.

**Acción:** publicar exactamente las diez herramientas declaradas entre este
FASER y el de control de UI. Ninguna otra.

**Resultado:** catálogo estable con sus esquemas.

**Error:** `MCP_PROTOCOL_ERROR` devuelve error MCP estándar y conserva el
proceso.

### Evento: `emulator.get_status`

**Condición:** no hay operación UI activa.

**Acción:**

1. Consultar ADB solo para el UDID configurado.
2. Consultar la salud de Appium.
3. Devolver versión Android, modelo, UDID y disponibilidad.

**Resultado:** `ok=true` sin cambiar aplicación visible, árbol UI ni captura.

**Error:** `EMULATOR_UNAVAILABLE` o `APPIUM_UNAVAILABLE`; no hay reintento
interno ni arranque de procesos.

### Evento: `ui.get_tree`

**Condición:** emulador disponible; no hay navegación activa. No requiere
Appium: va por ADB de solo lectura.

**Acción:** ejecutar la consulta ADB fija y de solo lectura `uiautomator dump`,
extraer el XML y reducirlo a lo que se puede leer y a lo que se puede accionar.
No abre sesión Appium.

**Resultado:** `foreground_package`, `texts` con lo que dice la pantalla,
`actions` con un objetivo por entrada y `can_scroll`. Cada acción trae el
selector que **este mismo servidor acepta** en `ui.tap` y `ui.type_text`, su
`role` (`button`, `input`, `toggle`, `long-press`), si está `enabled` y, cuando
ese selector encaja con más de un elemento, `ambiguous: true`.

El volcado completo no se entrega por defecto: cuesta unas diez veces más y
obliga a quien llama a interpretar XML. Se pide con `include_raw: true` y llega
en `ui_tree`.

**Error:** `UI_TREE_UNAVAILABLE`, también si el volcado no se puede interpretar.

### Evento: `screen.capture`

**Condición:** emulador disponible; no hay navegación activa. No requiere
Appium: va por ADB de solo lectura.

**Acción:** ejecutar la consulta ADB fija y de solo lectura `screencap -p`,
guardar una captura bajo `artifacts/` y no abrir sesión Appium.

**Resultado:** `artifact_id`, ruta local y `uri` `artifact://<artifact_id>`; sin
cambio UI intencionado. La imagen se lee como recurso MCP, de modo que un
cliente que no comparte disco con el arnés también puede verla.

**Error:** `EVIDENCE_WRITE_FAILED`; nunca afirmar éxito sin evidencia.

### Evento: `settings.open_apps`

**Condición:** emulador, Appium y bloqueo UI disponibles.

**Acción:**

1. Marcar `activeOperation=true`.
2. Validar UDID y punto final de Appium antes de conectar.
3. Abrir sesión y lanzar la intención Android fija
   `android.settings.APPLICATION_SETTINGS`. No se pulsa ningún elemento para
   llegar: la pantalla se pide por intención, no por navegación a ciegas.
4. Comprobar que el paquete visible es `com.android.settings`.
5. Esperar ≤8 s el marcador observable `All apps` y devolver su texto.
6. Guardar captura de éxito o fallo.
7. Cerrar sesión y liberar `activeOperation` en todos los desenlaces.

**Resultado:** pantalla Apps visible con evidencia asociada.

**Error:** `SETTINGS_FOREGROUND_FAILED`, `UI_ELEMENT_NOT_FOUND`,
`OPERATION_TIMEOUT` o `EMULATOR_BUSY`.

## VALIDACIONES

- El UDID identifica un emulador, nunca un teléfono físico. La comprobación vive
  en el adaptador ADB **y** en el creador de sesión Appium: toda herramienta
  entra por uno de los dos, así que no hay puerta sin guardia.
- `APPIUM_URL` apunta a un `http` en loopback. Se valida en el mismo sitio, no
  solo en la consulta de estado.
- Cada llamada tiene un `operationId` nuevo.
- Observación no puede invocar tap, input ni ADB mutante.
- Navegación usa selectores semánticos; coordenadas no forman parte del contrato.
- Toda sesión abierta se cierra incluso con timeout o excepción.
- La captura queda en `artifacts/`, directorio ignorado por Git.
- El recurso `artifact://{artifact_id}` sirve únicamente identificadores con la
  forma que este arnés emite, y comprueba que la ruta resuelta siga dentro de
  `artifacts/`. Un recorrido de directorios no es representable.
- Ninguna acción deja sesión Appium viva: se comprueba consultando al propio
  Appium antes y después de una tanda con éxito y con fallo.
- Cada captura usa una ruta única incluso en reintentos dentro del mismo segundo.
- Presupuesto: conexión ≤10 s, operación UI ≤30 s, espera de marcador ≤20 s.
- El transporte es stdio local; no se abre puerto de red.

## ERRORES Y FALLBACK

| Código | Causa | Recuperación |
|---|---|---|
| `EMULATOR_UNAVAILABLE` | UDID no disponible/no emulador | Pedir arrancar AVD; no usar Appium. |
| `APPIUM_UNAVAILABLE` | Appium no responde | Pedir iniciarlo; MCP no inicia procesos. |
| `EMULATOR_BUSY` | Navegación en curso | Rechazo inmediato; el cliente reintenta. |
| `SETTINGS_FOREGROUND_FAILED` | Paquete visible incorrecto | Cerrar sesión y capturar evidencia. |
| `UI_ELEMENT_NOT_FOUND` | Cambio de árbol/etiqueta | Adjuntar evidencia; nunca pulsar coordenadas. |
| `OPERATION_TIMEOUT` | Excede el tiempo | Cerrar sesión y liberar bloqueo. |
| `EVIDENCE_WRITE_FAILED` | Captura no grabable | Error explícito. |
| `INTERNAL_ERROR` | Error no clasificado | Cerrar sesión y devolver mensaje seguro. |

## RESULTADOS ESPERADOS

- El modelo sabe si el emulador está disponible antes de operar.
- El modelo puede leer pantalla y árbol UI sin mutarla.
- El modelo puede navegar a Apps de forma declarada y evidenciada.
- Ninguna herramienta gana capacidades implícitas por ser llamada desde MCP.

## FEEDBACK Y ACCESIBILIDAD

- Cada resultado incorpora `operation_id`, `tool` y `ok` para correlación.
- Los selectores priorizan `resource-id`, texto y `content-desc` antes que imagen
  o coordenadas.
- `ui.get_tree` expone etiquetas accesibles para no depender de visión si ya
  existe semántica.

## PRUEBAS Y ECA

- Dado Appium y emulador disponibles, `emulator.get_status` responde en ≤10 s y
  no cambia la app visible.
- Dos llamadas consecutivas a `ui.get_tree` o `screen.capture` no emiten una
  navegación ni cambian la pantalla.
- Desde Settings abierta o cerrada, `settings.open_apps` termina en Apps, deja
  evidencia y libera la sesión.
- Con Appium apagado, cualquier herramienta devuelve `APPIUM_UNAVAILABLE` sin
  bloquear ni lanzar procesos.
- Con UDID de teléfono o inexistente, el servidor rechaza antes de Appium: no
  sale ni una petición hacia el punto final, comprobado con un Appium espía.
- Con `APPIUM_URL` fuera de loopback, toda herramienta devuelve
  `APPIUM_UNAVAILABLE` sin llegar a la pila de red.
- Dos navegaciones concurrentes producen una sola sesión; la segunda recibe
  `EMULATOR_BUSY`.
- Un selector inexistente produce `UI_ELEMENT_NOT_FOUND`, evidencia y cero taps
  por coordenadas.
- Todo bug confirmado durante ECA se convierte en regresión versionada antes de
  corregirlo.

## DECISIONES

- Se elige MCP por stdio local antes que HTTP para evitar exposición de red.
- Se elige sesión temporal por operación para no dejar estado Appium huérfano.
- Se elige ADB de solo lectura para árbol y captura: crear una sesión Appium
  puede llevar una aplicación al frente y violaría la invariante de observación.
- Se elige bloqueo único porque el emulador es un recurso global.
- Se rechaza ADB shell arbitrario: rompería responsabilidad única y fronteras.
- Se pospone Auralis, Trinidad y Glas: serán clientes del MCP, no parte de su
  autoridad base.
