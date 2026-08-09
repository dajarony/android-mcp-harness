# CMCF — Android MCP Harness

## 1. Intención Global

Permitir que un agente controle y observe de forma reproducible un emulador
Android desechable, mediante herramientas MCP futuras, sin acceso al teléfono
personal ni al sistema anfitrión.

## 2. Alcance

**Incluye:** conexión Appium/UiAutomator2, lectura de UI, navegación en el
emulador, capturas y resultados normalizados.

**Excluye:** teléfono físico, automatización del anfitrión, Auralis/Trinidad,
instalación de APK ajenos y acciones irreversibles.

## 3. Bloques Principales

| BP | Propósito | Estado propio | Interfaz pública |
|---|---|---:|---|
| Entrada | Recibir configuración local o futuras llamadas MCP | No | `main()` |
| Sesión | Abrir/cerrar Appium contra un UDID explícito | Sí, efímero | `create_settings_driver()` |
| Navegación | Ejecutar una intención UI verificable | No | `navigate_to_apps()` |
| Evidencia | Producir capturas locales | No | `save_screenshot()` |
| Salida | Normalizar y presentar el resultado | No | `render_demo_result()` |

## 4. UAFs

- Entrada: cargar configuración de entorno y lanzar una demostración.
- Sesión: crear una sesión; cerrar esa misma sesión.
- Navegación: comprobar la app visible; navegar a Apps.
- Evidencia: reservar ruta; guardar captura.
- Salida: representar un resultado sin modificar estado.

## 5. Flujo de Datos

`variables locales → SettingsDemoConfig → controlador → sesión/navegación/evidencia → SettingsDemoResult → consola`.

## 6. Decisiones

- Se eligen selectores semánticos UiAutomator antes que coordenadas.
- Se conserva `scripts/demo_settings.py` como compatibilidad; delega en SUME.
- MCP se construirá como una entrada posterior; no se mezcla con Appium.

## 7. Siguiente Artefacto

FASER del servidor MCP y contratos de sus primeras herramientas de observación.
