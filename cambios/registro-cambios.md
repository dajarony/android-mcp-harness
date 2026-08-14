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

**Autor:** Dajarony Ysaac Guzmán Marmolejos.

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

**Autor:** Dajarony Ysaac Guzmán Marmolejos.

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

**Autor:** Dajarony Ysaac Guzmán Marmolejos.

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

**Autor:** Dajarony Ysaac Guzmán Marmolejos.

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

**Autor:** Dajarony Ysaac Guzmán Marmolejos.

---

## 2026-08-13 — Guardias de sesión aplicados en todas las puertas

**Archivos afectados:**

- Actualizado `logica/sesiones/appium.py`.
- Actualizado `logica/controladores/demo_settings.py`.
- Creado `tests/test_session_guards.py`.

**Motivo:**

- Una campaña ECA demostró que `assert_emulator_udid` y `assert_local_appium_url`
  solo se aplicaban en las herramientas de lectura. Con un `ANDROID_UDID` con
  forma de teléfono físico, las cinco herramientas que abren sesión enviaban un
  `POST /session` real a Appium: el arnés podía salir del emulador desechable.
- El banco anterior no lo vio porque comprobaba el UDID físico contra una sola
  herramienta, `emulator.get_status`.

**Hallazgos ECA y correcciones:**

- `create_device_driver` valida ahora UDID y punto final de Appium antes de
  conectar; es el embudo por el que pasan `ui.tap`, `ui.type_text`, `ui.scroll`,
  `device.back` y `settings.open_apps`.
- `run_settings_demo` conserva el código tipado de un `HarnessError` en vez de
  aplanarlo a `INTERNAL_ERROR`, para que el cliente sepa qué frontera se cerró.
- La regresión levanta un Appium espía y exige cero peticiones: si alguna
  herramienta futura evita el embudo, el test lo delata.

**Impacto:**

- Un UDID que no sea `emulator-<puerto>` recibe `EMULATOR_UNAVAILABLE` en las
  diez herramientas; un Appium fuera de loopback recibe `APPIUM_UNAVAILABLE`.
- Banco completo en verde: 20 pruebas unitarias y 6 secuencias reales contra el
  AVD, sin cambios de comportamiento en el camino feliz.

**Autor:** Dajarony Ysaac Guzmán Marmolejos.

---

## 2026-08-14 — Contrato al día con las diez herramientas

**Archivos afectados:**

- Actualizados `docs/faser/mcp-server.faser.md` y
  `docs/faser/android-ui-control.faser.md`.
- Actualizado `docs/modules/android-mcp-server.md`.
- Actualizados `mapa-global/arquitectura.yaml`, `package.json` y
  `entradas/mcp/server.py`.
- Limpiado `scripts/demo_settings.py`.

**Motivo:**

- El FASER del servidor seguía declarando cinco herramientas y describiendo
  cuatro, sin mencionar que las seis acciones semánticas tienen su contrato en
  un segundo documento. Quien llegaba al repositorio leía un producto distinto
  del que arranca.
- El proyecto declaraba tres versiones a la vez: `1.0.0` en `package.json`,
  `0.1.0` en el servidor y `0.2.0` en el mapa global.

**Correcciones:**

- El FASER del servidor declara ahora las diez herramientas y remite
  explícitamente al FASER de control de UI para las seis semánticas.
- Corregido el paso 4 de `settings.open_apps`: el flujo real lanza la intención
  fija `android.settings.APPLICATION_SETTINGS` y espera el marcador `All apps`;
  no pulsa ningún elemento para llegar.
- `ui.get_tree` y `screen.capture` dejan de exigir Appium en su condición: van
  por ADB de solo lectura.
- Documentados los guardias de UDID y de punto final como validación del
  contrato, con su prueba de Appium espía.
- Añadido `input_hint` al bloque de selectores del FASER de control, donde solo
  aparecía en la aclaración final.
- Versión única `0.3.0` en manifiesto, servidor y mapa.
- Eliminado el bloque `__main__` duplicado del script de compatibilidad.
- `appium-session` declara su dependencia real de la frontera de seguridad.

**Impacto:**

- Documentación y código describen el mismo sistema.
- El oráculo ECA no se ha tocado: extenderlo con los identificadores de las
  herramientas nuevas es decisión humana, no de quien es medido por él.
- Banco completo en verde: 20 pruebas unitarias y 6 secuencias reales contra el
  AVD.

**Autor:** Dajarony Ysaac Guzmán Marmolejos.

---

## 2026-08-14 — Cerrados los cinco hallazgos de comportamiento

**Archivos afectados:**

- Actualizados `contratos/ui_control.py`, `logica/controladores/demo_settings.py`,
  `logica/sesiones/appium.py` y `logica/servicios/mcp_server/controller.py`.
- Creado `tests/test_error_contracts.py`; corregido `tests/test_contracts.py`.

**Motivo:**

- Una campaña ECA contra el emulador real encontró cinco promesas rotas que el
  banco anterior no podía ver, porque cada test comprobaba funcionamiento y no
  comportamiento.

**Correcciones:**

- El mensaje público de una navegación fallida ya no repite la excepción: la
  causa va al registro local y el cliente recibe texto redactado por el
  proyecto. `tests/test_contracts.py` congelaba la fuga como salida correcta.
- Las herramientas de acción devuelven `APPIUM_UNAVAILABLE` cuando Appium está
  parado, en vez de `INTERNAL_ERROR`: el creador de sesión consulta el estado
  antes de conectar y reutiliza el adaptador ya probado.
- `validate_text` y `validate_selector` rechazan caracteres de control y
  overrides bidireccionales. Un salto de línea en un `EditText` es la acción
  IME, no texto, y no forma parte del contrato de `ui.type_text`.
- `validate_package_name` admite un paquete de un solo segmento: `android` es
  real, lo listaba `app.list_installed` y lo rechazaba el propio validador.
- `app.open` espera hasta 6 s a que el paquete se haga visible y reintenta si el
  volcado del árbol falla durante una transición. Antes leía una sola vez y aun
  así informaba de un tiempo de espera que no existía.

**Impacto:**

- Campaña ECA relanzada entera: 56 casos correctos frente a 46, cero fallos
  frente a tres.
- Banco completo en verde: 30 pruebas unitarias y 7 secuencias reales contra el
  AVD.

**Autor:** Dajarony Ysaac Guzmán Marmolejos.

---

## 2026-08-14 — Integración continua en dos flujos

**Archivos afectados:**

- Creados `.github/workflows/ci.yml` y `.github/workflows/eca.yml`.
- Actualizados `README.md` y `tests/test_error_contracts.py`.

**Motivo:**

- El proyecto se apoya en medir, no en suponer, y no tenía ninguna medida
  automática al recibir un cambio.

**Decisiones:**

- Se separan dos flujos a propósito. `ci.yml` bloquea: banco unitario en Python
  3.12 y 3.13 más una comprobación del catálogo MCP por stdio real en un
  proceso aparte. `eca.yml` no bloquea: arranca un AVD y Appium de verdad,
  semanalmente o a demanda, y sube las capturas como artefacto.
- Un emulador en integración continua es lento y a veces caprichoso. Una puerta
  que se pone roja sin culpa del código enseña a ignorar el rojo, así que la
  campaña real informa en lugar de bloquear.
- El puerto muerto de las pruebas deja de estar fijado a 4799: se reserva y
  libera uno efímero, para que el resultado no dependa de qué escucha en la
  máquina que ejecuta.

**Impacto:**

- Cada cambio queda medido antes de fusionarse.
- La evidencia de la campaña real queda descargable durante 14 días.

**Autor:** Dajarony Ysaac Guzmán Marmolejos.

---

## 2026-08-14 — Selectores y observación de flujo verificados en Android 16

**Archivos afectados:**

- Actualizados el resumen semántico, el controlador MCP, su entrada, contratos
  FASER, README y regresiones.

**Motivo:**

- La campaña ECA real encontró tres botones de Settings anunciados por texto
  aunque sus etiquetas vivían en hijos `content-desc`; además, una lectura tras
  escribir dentro de un flujo debía observar el mismo driver que preserva ese
  estado.

**Corrección:**

- El resumen conserva el atributo real del descendiente accesible en vez de
  convertirlo en `text`. `ui.get_tree(session_id?)` reutiliza el `page_source`
  del flujo propietario cuando se solicita una instantánea intermedia.

**Verificación:**

- ECA contra Android 16 + Appium: 10/10 casos aplicables correctos; el caso de
  app objetivo queda omitido hasta instalar un APK. Banco unitario: 102 pruebas
  correctas.

**Autor:** Dajarony Ysaac Guzmán Marmolejos.

---

## 2026-08-14 — Desambiguación por contexto semántico

**Archivos afectados:**

- Actualizados `contratos/ui_control.py`, `logica/navegacion/resumen.py` y
  `logica/navegacion/semantica.py`.
- Actualizados pruebas MCP, FASER y README.

**Motivo:**

- Dos botones con la misma etiqueta eran correctamente declarados `ambiguous`,
  pero el agente no podía elegir uno aunque Android sí expusiera un ancestro
  semántico que los distinguía.

**Corrección:**

- Un selector puede llevar `within` con una sola clave semántica no anidada. El
  resumen la publica únicamente si reduce los candidatos a uno; el localizador
  la convierte en una condición de ancestro XPath generada por el servidor, no
  aportada por el cliente.
- Cuando no hay contexto que pruebe unicidad, `ambiguous` se conserva y el toque
  sigue rechazando la moneda al aire.

**Verificación:**

- Regresiones de resumen, contrato y transporte MCP en verde.

**Autor:** Dajarony Ysaac Guzmán Marmolejos.

---

## 2026-08-14 — La pantalla, traducida al vocabulario del propio servidor

**Archivos afectados:**

- Creado `logica/navegacion/resumen.py`; creado `tests/test_screen_summary.py`.
- Actualizados `logica/servicios/mcp_server/controller.py`,
  `logica/evidencias/capturas.py` y `entradas/mcp/server.py`.
- Actualizados `tests/test_mcp_emulator_e2e.py`, `.github/workflows/eca.yml`,
  FASER del servidor, documento de módulo y `README.md`.

**Motivo:**

- `ui.get_tree` devolvía el volcado XML entero. Quien llamaba pagaba miles de
  tokens de maquetación para encontrar una etiqueta y aún tenía que traducirla
  por su cuenta al selector que este servidor acepta.
- `screen.capture` devolvía una ruta local: un cliente que no comparte disco con
  el arnés no podía ver nada.
- La promesa de no dejar sesiones Appium vivas nunca se había medido.

**Correcciones:**

- `ui.get_tree` responde qué dice la pantalla (`texts`) y qué se puede accionar
  (`actions`), y cada acción trae el selector que `ui.tap` y `ui.type_text`
  aceptan, su `role`, si está habilitada y si es `ambiguous`. Medido sobre la
  lista de aplicaciones de Ajustes: 1.815 bytes frente a 17.508, un 90 % menos.
  El volcado sigue disponible con `include_raw`.
- Los contenedores desplazables no se ofrecen como objetivos: `ui.scroll` actúa
  sobre la pantalla y no acepta selector, así que se expone `can_scroll` en vez
  de un blanco que no se puede apuntar y que además tomaba prestada la etiqueta
  de su primer hijo.
- La evidencia se publica como recurso MCP `artifact://{artifact_id}`. Solo
  sirve identificadores con la forma que el arnés emite y comprueba que la ruta
  resuelta siga dentro de `artifacts/`.
- La campaña recorre dos niveles de API, no uno.
- Añadida `INV-SESION-1`: se pregunta a Appium cuántas sesiones tiene antes y
  después de una tanda con éxitos y con fallos. Requiere arrancar Appium con
  `--allow-insecure='*:session_discovery'`, así que es explícita: una promesa
  sin medir no es una promesa cumplida, y fingir lo contrario es peor que decir
  que nunca se comprobó.

**Impacto:**

- Un modelo lee la pantalla, elige una entrada y la envía sin interpretar XML,
  sin calcular posiciones y sin adivinar. `FLOW-SEL-1` lo comprueba contra el
  AVD: un selector salido de `ui.get_tree` acierta en `ui.tap`.
- Banco completo en verde: 45 pruebas unitarias y 9 secuencias reales contra el
  AVD, con cero sesiones Appium al terminar.

**Autor:** Dajarony Ysaac Guzmán Marmolejos.

---

## 2026-08-14 — Una captura tiene que mostrar algo

**Archivos afectados:**

- Creado `logica/evidencias/imagen.py`; creado `tests/test_evidence_is_evidence.py`.
- Actualizados `logica/infraestructura/adb.py`, `logica/evidencias/capturas.py`,
  `logica/navegacion/resumen.py` y `logica/servicios/mcp_server/controller.py`.
- Actualizados `tests/test_screen_summary.py`, `.github/workflows/eca.yml`,
  FASER del servidor, mapa global y `README.md`.

**Motivo:**

- Conduciendo el emulador como cliente MCP se miraron las capturas en vez de las
  aserciones: las doce de la sesión eran un rectángulo blanco. Un solo color,
  10.195 bytes exactos, por ADB y por Appium. El arnés devolvió `ok: true` en las
  doce, porque solo comprobaba los bytes mágicos del PNG y la campaña solo
  comprobaba que el fichero existiera.
- La causa era el emulador arrancado con `-gpu swiftshader_indirect`, que es
  justo lo que usaba el flujo de campaña recién escrito: en integración continua
  se habrían subido cuarenta pruebas en blanco y todo habría pasado en verde.

**Correcciones:**

- Nuevo decodificador PNG con la biblioteca estándar, sin dependencias añadidas,
  que responde si una imagen tiene alguna variación. Cuesta 25 ms sobre
  1080x2400 y no juzga lo que no entiende: un PNG entrelazado se deja pasar en
  vez de rechazarse por las bravas.
- Las dos vías de captura, ADB y Appium, rechazan una imagen plana con
  `EVIDENCE_WRITE_FAILED`, y la de Appium borra el fichero para que nadie lo
  confunda luego con una prueba.
- La campaña usa `-gpu swiftshader` directo, que sí produce fotogramas reales.
- `bounds` y `screen` se publican para auditar la maqueta, con `layout_findings`
  para lo que una máquina puede demostrar: fuera de pantalla, sin área, o control
  menor que 48 dp en ambos ejes, convertidos con la densidad real leída del
  dispositivo. La posición nunca se acepta como selector de entrada.

**Hallazgos ECA y correcciones:**

- El primer criterio de tamaño denunciaba una fila de 1080x84 en los Ajustes de
  Android. Era un falso positivo: una fila ancha recortada por el scroll, no un
  botón diminuto. El criterio pasó a exigir que ambos ejes queden por debajo del
  mínimo, y la pantalla volvió a dar cero hallazgos, que es lo correcto.

**Impacto:**

- La evidencia de la campaña pasó de 10.195 bytes idénticos a 100-195 KB con
  contenido real.
- Banco completo en verde: 58 pruebas unitarias y 10 secuencias reales contra el
  AVD, con cero sesiones Appium al terminar.

**Autor:** Dajarony Ysaac Guzmán Marmolejos.

---

## 2026-08-14 — El presupuesto de conexión se midió en una máquina caliente

**Archivos afectados:**

- Actualizados `contratos/demo_settings.py`, `logica/sesiones/appium.py`,
  `entradas/mcp/server.py` y `entradas/comandos/demo_settings.py`.
- Actualizados `tests/test_error_contracts.py`, `.github/workflows/eca.yml` y el
  FASER del servidor.

**Motivo:**

- La primera ejecución real de la campaña en integración continua falló cuatro
  secuencias con `INTERNAL_ERROR`. La causa, en el registro local: `TimeoutError`
  al abrir la sesión Appium.
- Abrir una sesión UiAutomator2 instala y arranca una aplicación servidor en el
  dispositivo. En frío son decenas de segundos. El presupuesto de 10 s del
  contrato se midió en una máquina ya caliente y se escribió como si fuera
  universal; en hardware más lento, toda acción de UI fallaba.

**Correcciones:**

- Presupuesto de conexión configurable con `ANDROID_MCP_CONNECT_TIMEOUT`, 120 s
  por defecto, separado del presupuesto de operación.
- Agotarlo devuelve `OPERATION_TIMEOUT`, el código que el FASER ya declaraba,
  en vez de `INTERNAL_ERROR`.
- El `default` del parámetro de nivel de API anulaba la matriz: una ejecución
  manual corría un solo nivel en vez de los dos. Eliminado.

**Impacto:**

- La campaña deja de depender de que la máquina que la ejecuta sea rápida.
- Un cliente puede distinguir "tarda demasiado" de "algo desconocido ha fallado".

**Autor:** Dajarony Ysaac Guzmán Marmolejos.

---

## 2026-08-14 — La pista de un campo no vive en el mismo sitio en cada Android

**Archivos afectados:**

- Actualizado `logica/navegacion/semantica.py`.
- Actualizados `tests/test_screen_summary.py` y el FASER de control de UI.

**Motivo:**

- La campaña corrió por primera vez sobre dos niveles de API. En API 36 pasó
  entera; en API 34 falló `FLOW-TEXT-1`, escribir en el buscador de Ajustes.
- La causa se leyó en la evidencia, no en el código: la captura de fallo que el
  arnés guarda automáticamente mostraba el buscador ya abierto, con el teclado
  arriba y el marcador `Search...` dibujado. El toque había funcionado; lo que no
  encontraba nada era el selector.

**Correcciones:**

- `input_hint` construía un XPath que exigía un descendiente con `content-desc`,
  la forma que usa Compose en Android 16. Un `EditText` clásico lleva la pista en
  sí mismo y no tiene hijos, así que en Android 14 no coincidía con nada.
- Ahora busca en los cuatro sitios donde Android guarda esa pista: `hint`,
  `content-desc` y `text` propios, y `content-desc` de un descendiente. Un
  atributo ausente simplemente no coincide, así que preguntar por los cuatro no
  cuesta nada.
- Documentado el límite: una vez escrito el campo, su `text` deja de ser la
  pista. El selector sirve para encontrar el campo, no para volver a él lleno.

**Impacto:**

- El selector deja de estar atado a una versión de Android, que es justo lo que
  vino a evitar.
- Sin regresión en API 36: campaña local completa en verde.

**Autor:** Dajarony Ysaac Guzmán Marmolejos.

---

## 2026-08-14 — Seis intentos hasta que el arnés se delató solo

**Archivos afectados:**

- Actualizados `logica/navegacion/semantica.py` y `logica/navegacion/resumen.py`.
- Actualizados `tests/test_screen_summary.py` y `tests/test_mcp_emulator_e2e.py`.

**Motivo:**

- La campaña corrió por primera vez sobre dos niveles de API. `FLOW-TEXT-1`
  fallaba en API 34 y pasaba en API 36. Hicieron falta seis vueltas, y las cinco
  primeras encontraron obstáculos para poder ver, no la causa.

**Hallazgos ECA y correcciones, en orden:**

1. `input_hint` exigía un descendiente con `content-desc`, la forma de Compose en
   Android 16. Ampliado a los cuatro sitios donde Android guarda una pista.
2. El mensaje de `UI_ELEMENT_NOT_FOUND` no decía nada útil. Ahora nombra hasta
   diez objetivos que la pantalla sí ofrece, con su papel. Un callejón sin salida
   que nombra las alternativas es un reintento.
3. Dieciocho aserciones de la campaña eran `assertTrue(resultado["ok"])` sin
   mensaje: construían el diagnóstico y lo tiraban en la aserción.
4. El resumidor solo entendía una de las dos formas del volcado. `uiautomator
   dump` llama `<node>` a cada elemento; el `page_source` de Appium lo nombra con
   su clase. Contra la segunda encontraba cero elementos.
5. El localizador exigía la clase exacta `android.widget.EditText`. El buscador
   es `EditText` en una versión y `AppCompatEditText` en otra. Comparado ahora
   por sufijo.
6. La causa real: el resumen buscaba la pista de un descendiente por texto o por
   descripción, y el localizador solo por descripción. El resumen anunciaba
   `'Search…' (input)` mientras el localizador no encontraba nada.

**Impacto:**

- Un sistema que se contradice entre lo que anuncia y lo que acepta es el peor
  fallo posible aquí: si la lista de objetivos no es fiable, no vale nada. Queda
  una prueba que compara las dos piezas entre sí para que no vuelvan a divergir
  en silencio.
- Campaña en verde sobre API 34 y API 36. 71 pruebas unitarias y 10 secuencias
  reales por nivel.

**Autor:** Dajarony Ysaac Guzmán Marmolejos.

---

## 2026-08-14 — Un diagnóstico de entorno y una imagen que se prueba sola

**Archivos afectados:**

- Creados `contratos/diagnostico.py`, `logica/diagnostico/entorno.py`,
  `salidas/consola/doctor.py`, `entradas/comandos/doctor.py` y
  `tests/test_doctor.py`.
- Creados `Dockerfile` y `.dockerignore`.
- Actualizados `logica/infraestructura/adb.py`, `mapa-global/arquitectura.yaml`
  y `README.md`.

**Motivo:**

- La fricción real de instalación no son las dependencias de Python: son el JDK,
  el SDK y el emulador. Un error de cada vez convierte la puesta en marcha en un
  juego de adivinanzas.

**Hallazgos y correcciones:**

- `resolve_adb_path` buscaba `adb.exe` a fuego dentro del SDK. Fuera de Windows
  esa rama no coincidía nunca y el arnés funcionaba por accidente, gracias al
  respaldo del PATH. Ahora prueba ambos nombres.
- `doctor` comprobaba que `java` existiera. En su primera ejecución encontró un
  Java 8 en el PATH de la máquina de desarrollo, con el que UiAutomator2 no
  arranca. Comprobar que un programa existe es como se pasa una revisión y se
  falla una hora después: ahora se lee la versión mayor, en los dos esquemas de
  numeración de Java.

**Decisiones:**

- El emulador no entra en la imagen. Necesita `/dev/kvm`, que Docker Desktop en
  Windows y macOS no cede de forma fiable, y UiAutomator2 reenvía puertos del
  dispositivo por el servidor ADB: esos reenvíos quedarían en el anfitrión,
  inalcanzables desde dentro. Documentado en el propio Dockerfile.
- Lo que la imagen sí demuestra se ha ejecutado antes de escribirlo: 81 pruebas
  en verde dentro del contenedor y el catálogo MCP completo por stdio real.

**Impacto:**

- Cualquiera puede verificar el arnés con dos órdenes y sin instalar nada.
- Quien vaya a la campaña real sabe exactamente qué le falta y cómo arreglarlo.

**Autor:** Dajarony Ysaac Guzmán Marmolejos.

---

## 2026-08-14 — Lo que el teclado tapa

**Archivos afectados:**

- Actualizados `logica/infraestructura/adb.py`, `logica/navegacion/resumen.py`
  y `logica/servicios/mcp_server/controller.py`.
- Actualizados `tests/test_screen_summary.py`, FASER del servidor y `README.md`.

**Motivo:**

- Conduciendo una aplicación Flutter real, `ui.get_tree` ofrecía la barra de
  pestañas mientras `ui.tap` no podía tocarla. Medido: con `mInputShown=true` el
  toque devolvía `UI_ELEMENT_NOT_FOUND`; con el teclado cerrado, `OK`.
- La causa: el teclado no aparece en el volcado de `uiautomator`. El volcado
  describe la ventana de la aplicación como si nada estuviera encima, así que lo
  cubierto se leía como disponible.

**Correcciones:**

- Nueva lectura fija de ADB del marco del teclado, tomada de los insets de
  ventana de Android, que es donde sí está.
- Los objetivos bajo ese marco se marcan `covered_by_keyboard`, y el resumen
  incluye `keyboard: {open, top}`. No se ocultan: ocultarlos sería mentir por
  omisión, y `device.back` cierra el teclado, así que quien llama puede actuar.

**Impacto:**

- Tercera y última aparición de la misma familia de fallo: el resumen anunciando
  una puerta que el localizador niega. Las dos anteriores se cerraron ayer y hoy.
- Verificado contra el dispositivo: con el teclado abierto las tres pestañas se
  marcan y el toque falla como el arnés había avisado; al cerrarlo, cero marcas
  y el toque funciona.

**Autor:** Dajarony Ysaac Guzmán Marmolejos.

---

## 2026-08-14 — El resumen y el localizador se comprueban completos

**Archivos afectados:**

- Actualizado `tests/test_mcp_emulator_e2e.py`.
- Actualizados `docs/eca/mcp-emulator-v1.md` y `README.md`.

**Motivo:**

- `FLOW-SEL-1` comprobaba un selector elegido de la pantalla. Era una señal
  útil, pero no demostraba que el resto del vocabulario que `ui.get_tree`
  publica se resolviera con el mismo localizador que usan `ui.tap` y
  `ui.type_text`.

**Corrección:**

- `FLOW-SEL-ALL-1` abre la pantalla estable de Apps, lee sus objetivos y, en
  una única sesión Appium, resuelve cada selector habilitado que no es ambiguo
  ni está cubierto por el teclado. No pulsa los objetivos: pulsar el primero
  cambiaría la pantalla y haría imposible comprobar los demás contra el mismo
  estado.

**Impacto:**

- La promesa del resumen ya no se mide con un ejemplo. Cada destino que se
  anuncia como alcanzable tiene que existir para el localizador semántico antes
  de que la campaña ECA pueda quedar en verde.

**Autor:** Dajarony Ysaac Guzmán Marmolejos.

---

## 2026-08-14 — Flujos UI explícitos sin sesiones huérfanas

**Archivos afectados:**

- Creado `logica/sesiones/flujo.py` y su banco `tests/test_ui_flow_sessions.py`.
- Actualizados contrato MCP, controlador, entrada MCP, FASER, ECA, mapa y README.

**Motivo:**

- El cierre de driver por cada acción protegía el emulador, pero hacía perder el
  foco y el texto entre `ui.type_text` y la acción siguiente. Reutilizar un
  driver implícitamente habría creado un propietario invisible y sesiones
  huérfanas.

**Corrección:**

- `ui.session.open` crea un único driver y devuelve un `session_id` opaco.
  `ui.tap`, `ui.type_text`, `ui.scroll` y `device.back` lo aceptan de forma
  opcional; cada uso renueva 60 s de inactividad. `ui.session.close` lo libera
  antes y el temporizador lo cierra si el cliente desaparece.
- Una mutación que no presenta el token mientras existe un flujo recibe
  `EMULATOR_BUSY`; un token inválido o caducado recibe `INVALID_UI_SESSION`.

**Verificación:**

- Banco unitario: 90 pruebas en verde; 11 ECA omitidas sin AVD/Appium.

**Autor:** Dajarony Ysaac Guzmán Marmolejos.

---

## 2026-08-14 — Scroll cardinal para carruseles

**Archivos afectados:**

- Actualizados `contratos/ui_control.py` y `logica/navegacion/semantica.py`.
- Creado `tests/test_semantic_navigation.py`; actualizados FASER, ECA y README.

**Motivo:**

- `ui.scroll` solo podía avanzar verticalmente. Las pantallas de bienvenida y
  carruseles horizontales seguían fuera de la frontera semántica.

**Corrección:**

- `direction` acepta ahora `up`, `down`, `left` y `right`. Expresa el movimiento
  del contenido; el servidor genera el arrastre opuesto, fijo y centrado, sin
  recibir coordenadas, distancia ni duración desde el cliente.

**Verificación:**

- Regresiones cubren las cuatro direcciones y la geometría normalizada de cada
  gesto.

**Autor:** Dajarony Ysaac Guzmán Marmolejos.

---

## 2026-08-14 — Cliente MCP de referencia declarativo

**Archivos afectados:**

- Creados contrato, runner, entrada de consola, salida JSON, ejemplo y pruebas.
- Actualizados README, FASER y mapa global.

**Motivo:**

- El arnés exponía herramientas seguras, pero faltaba una aplicación externa
  pequeña que demostrase una tarea completa por stdio y dejase un informe
  reutilizable sin convertir al cliente en otro agente con autoridad propia.

**Corrección:**

- El flujo JSON declara un paquete y pasos semánticos; el cliente abre la app,
  observa, abre y cierra su propia sesión, ejecuta los pasos y emite cada
  respuesta MCP con su evidencia. El archivo no puede aportar un `session_id`.

**Verificación:**

- Pruebas cubren orden de transporte, inyección del token y cierre incluso tras
  un fallo de UI.

**Autor:** Dajarony Ysaac Guzmán Marmolejos.
