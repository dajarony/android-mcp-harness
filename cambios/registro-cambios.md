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
