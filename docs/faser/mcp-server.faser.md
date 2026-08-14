===============================================================
Componente: Android Emulator MCP Server
Tipo: Service / MCP Gateway
Version: 0.8.0
Estado: Implementado y verificado en emulador local
===============================================================

> **Alcance de este documento.** Aquí vive la frontera del servidor: catálogo,
> contrato común de salida, exclusividad, evidencia y las cuatro herramientas de
> observación más la navegación declarada `settings.open_apps`. Las seis
> herramientas de control semántico (`app.list_installed`, `app.open`, `ui.tap`,
> `ui.type_text`, `ui.scroll`, `device.back`) tienen su contrato propio en
> [`android-ui-control.faser.md`](android-ui-control.faser.md). El catálogo
> completo son **doce** herramientas y ninguna gana capacidades por estar
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
| `activeOperation` | `bool`, `false` | `EmulatorOperationGate` | Solo una operación UI por emulador. |
| `evidencePath` | `str \| null`, `null` | evidencia | Siempre bajo `artifacts/`. |
| `activeUiFlow` | `session_id \| null`, `null` | gestor de flujo | Único, opaco, con caducidad por inactividad. |

Los estados viven solo durante una operación, salvo el archivo de evidencia y
un flujo UI explícito. Este último mantiene un único driver solo mientras su
`session_id` opaco se renueva; caduca y se cierra tras 60 s sin uso.

## ENTRADAS

- `tools/list`: catálogo MCP sin parámetros.
- `emulator.get_status`: lectura de ADB y salud de Appium.
- `ui.get_tree(include_raw?, session_id?)`: lectura del árbol de accesibilidad/UI;
  con token, observa el estado intermedio de ese flujo Appium.
- `screen.capture`: captura local de la pantalla actual.
- `app.list_installed`: lectura de paquetes instalados.
- `settings.open_apps`: navegación declarada de Ajustes a Apps.
- `ui.session.open`: reserva un flujo Appium exclusivo y devuelve un
  `session_id` opaco.
- `ui.session.close(session_id)`: cierra el flujo correspondiente.

Definidas en [`android-ui-control.faser.md`](android-ui-control.faser.md) y
servidas por este mismo proceso, contrato y bloqueo:

- `app.open(package_name)`, `ui.tap(selector)`,
  `ui.type_text(selector, text, session_id?)`, `ui.scroll(direction, session_id?)`,
  `device.back(session_id?)`. `ui.tap` también acepta `session_id?`.

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

**Acción:** publicar exactamente las doce herramientas declaradas entre este
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

**Condición:** emulador disponible. Sin token, no hay flujo UI activo y la
lectura no requiere Appium. Con `session_id`, el token debe pertenecer al flujo
activo.

**Acción:** sin token, ejecutar la consulta ADB fija y de solo lectura
`uiautomator dump`. Con token, reutilizar el `page_source` del driver que posee
el flujo. En ambos casos reducir el XML a lo que se puede leer y accionar; la
lectura nunca abre una segunda sesión Appium.

**Resultado:** `foreground_package`, `texts` con lo que dice la pantalla,
`actions` con un objetivo por entrada y `can_scroll`. Cada acción trae el
selector que **este mismo servidor acepta** en `ui.tap` y `ui.type_text`, su
`role` (`button`, `input`, `toggle`, `long-press`), si está `enabled`, su
`bounds` para auditoría y, cuando ese selector encaja con más de un elemento,
`ambiguous: true`. Si un ancestro semántico deja uno solo de esos destinos, el
selector lleva `within` y `disambiguated: true`; nunca recibe posiciones ni
XPath de quien llama. Acompañan `screen`, `layout_findings` y `keyboard`.

El teclado no aparece en el volcado de `uiautomator`: el volcado describe la
ventana de la aplicación como si nada estuviera encima. Por eso se lee su marco
aparte, de los insets de ventana de Android, y todo objetivo que caiga bajo él
se marca `covered_by_keyboard`. No se oculta: ocultarlo sería mentir por
omisión, y `device.back` cierra el teclado, así que quien llama puede actuar.

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

**Error:** `EVIDENCE_WRITE_FAILED`; nunca afirmar éxito sin evidencia, y una
captura de un solo color plano no es evidencia: se rechaza igual que un PNG
inválido.

### Evento: `ui.session.open` y `ui.session.close`

**Condición:** Appium disponible y ningún flujo UI activo.

**Acción:** abrir un único driver Appium y devolver un identificador opaco. Las
acciones UI que presenten ese identificador reutilizan el mismo driver y
renuevan su plazo de inactividad. `ui.session.close` exige el mismo identificador
y lo cierra inmediatamente; tras 60 s sin uso un temporizador también lo cierra.

**Resultado:** una cadena escribir-y-enviar puede conservar la pantalla y el
foco. Un cliente que no presente el identificador conserva el comportamiento
anterior: driver temporal por acción.

**Qué ocurre si nadie cierra el flujo.** Hay tres redes, por orden:

1. **60 s sin uso** (`ANDROID_MCP_FLOW_IDLE_TIMEOUT`): un temporizador cierra el
   driver. Cada acción que presenta el identificador renueva ese plazo.
2. **El proceso muere antes de que salte.** Entonces el arnés ya no puede cerrar
   nada y la sesión queda viva en Appium hasta que su propio
   `newCommandTimeout` de 60 s la retira. Es la única ventana en la que la
   promesa de no dejar sesiones huérfanas depende de un tercero, y se declara
   aquí en vez de fingir que no existe.
3. **Una acción que se cuelga** no puede agotar el plazo de inactividad, porque
   retiene el bloqueo del emulador mientras dura. Para eso está el techo de
   acción descrito abajo.

**Techo por acción** (`ANDROID_MCP_ACTION_TIMEOUT`, 90 s): pasado ese punto el
arnés deja de esperar, devuelve `OPERATION_TIMEOUT`, **anula el arriendo del
flujo** —el driver quedó en estado desconocido— y libera el emulador. No es el
presupuesto declarado de ≤30 s, que es un objetivo: es el límite que garantiza
que una sola llamada colgada no bloquee a todos los clientes.

El hilo abandonado sigue corriendo hasta que termine solo, porque un hilo no se
puede matar. Se acepta a sabiendas: lo que importa es que el bloqueo se suelte.

**Error:** `EMULATOR_BUSY` si ya hay un flujo y `INVALID_UI_SESSION` si el token
es malformado, ajeno o ya ha caducado.

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
- Toda sesión abierta se cierra incluso con timeout o excepción. Un flujo
  explícito sobrevive entre llamadas a propósito, pero nunca sin plazo: 60 s de
  inactividad, un techo de 90 s por acción, y el cierre a petición.
- Un flujo UI solo se usa con el token opaco que lo abrió, no se comparte, y se
  cierra de forma explícita o por caducidad de inactividad.
- La captura queda en `artifacts/`, directorio ignorado por Git.
- Toda captura se decodifica antes de aceptarse. Si todos sus píxeles son
  idénticos, la prueba no prueba nada y se rechaza. Se asume el intercambio: una
  pantalla realmente uniforme de borde a borde también sería rechazada, y en
  Android eso es prácticamente imposible.
- `bounds` y `screen` se publican para auditar la maqueta, y `layout_findings`
  denuncia solo lo inequívoco: fuera de pantalla, sin área, o control menor que
  48 dp en ambos ejes. La posición nunca se acepta como selector de entrada.
- El recurso `artifact://{artifact_id}` sirve únicamente identificadores con la
  forma que este arnés emite, y comprueba que la ruta resuelta siga dentro de
  `artifacts/`. Un recorrido de directorios no es representable.
- Ninguna acción deja sesión Appium viva: se comprueba consultando al propio
  Appium antes y después de una tanda con éxito y con fallo.
- Cada captura usa una ruta única incluso en reintentos dentro del mismo segundo.
- Presupuesto de conexión: `ANDROID_MCP_CONNECT_TIMEOUT`, 120 s por defecto.
  Abrir una sesión UiAutomator2 instala y arranca una aplicación servidor en el
  dispositivo: en frío son decenas de segundos, y el antiguo límite de 10 s solo
  se cumplía en una máquina ya caliente. Agotarlo devuelve `OPERATION_TIMEOUT`,
  nunca `INTERNAL_ERROR`.
- Presupuesto de operación UI ≤30 s una vez abierta la sesión; espera de marcador
  ≤20 s.
- El transporte es stdio local; no se abre puerto de red.

## ERRORES Y FALLBACK

| Código | Causa | Recuperación |
|---|---|---|
| `EMULATOR_UNAVAILABLE` | UDID no disponible/no emulador | Pedir arrancar AVD; no usar Appium. |
| `APPIUM_UNAVAILABLE` | Appium no responde | Pedir iniciarlo; MCP no inicia procesos. |
| `EMULATOR_BUSY` | Navegación en curso | Rechazo inmediato; el cliente reintenta. |
| `INVALID_UI_SESSION` | Token ausente, ajeno o caducado | Abrir un flujo nuevo; nunca reutilizar un driver desconocido. |
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
- Un flujo conserva el mismo driver para varias acciones, rechaza un segundo
  propietario y cierra su driver tanto al cerrarse como al caducar.
- Un selector inexistente produce `UI_ELEMENT_NOT_FOUND`, evidencia y cero taps
  por coordenadas.
- Todo bug confirmado durante ECA se convierte en regresión versionada antes de
  corregirlo.

## DECISIONES

- Se elige MCP por stdio local antes que HTTP para evitar exposición de red.
- Se elige sesión temporal por operación como valor por defecto. El flujo
  explícito añade continuidad sin estado huérfano: su token no es adivinable,
  tiene un solo propietario y caduca.
- Se elige ADB de solo lectura para árbol y captura: crear una sesión Appium
  puede llevar una aplicación al frente y violaría la invariante de observación.
- Se elige bloqueo único porque el emulador es un recurso global.
- Se rechaza ADB shell arbitrario: rompería responsabilidad única y fronteras.
- Se pospone Auralis, Trinidad y Glas: serán clientes del MCP, no parte de su
  autoridad base.
