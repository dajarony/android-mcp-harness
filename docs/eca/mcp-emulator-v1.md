# ECA — MCP Android Emulator v1

> Contrato de evaluación independiente. Los tests lo ejecutan, pero no lo
> modifican. El emulador objetivo es desechable (`emulator-5554`), nunca un
> dispositivo físico.

## Oráculo humano

| ID | Herramienta / flujo | Promesa verificable | Evidencia exigida |
|---|---|---|---|
| INV-OBS-1 | `emulator.get_status`, `ui.get_tree`, `screen.capture` | Observar no cambia la pantalla visible ni inicia una sesión Appium. | Paquete visible igual antes/después; PNG local para captura. |
| FLOW-NAV-1 | `settings.open_apps` | La única acción de UI permitida llega a Apps de Settings. | `com.android.settings`, marcador `Apps` y PNG bajo `artifacts/`. |
| INV-SAFE-1 | Cualquier herramienta | Solo acepta `emulator-<puerto>` y Appium loopback. | Error tipado; no se abre sesión ni se ejecuta ADB mutante. |
| INV-CONC-1 | Dos operaciones simultáneas | No hay dos dueños del emulador. | Segunda llamada: `EMULATOR_BUSY`. |
| SEQ-EVID-1 | Dos `screen.capture` consecutivas | Un reintento no sobrescribe evidencia previa. | Dos `artifact_id` diferentes y ambos PNG existentes. |
| CONTRACT-STDIO-1 | Proceso MCP stdio | El cliente real descubre el catálogo y llama estado sin red. | `tools/list` exacto y respuesta estructurada. |
| FLOW-UI-1 | `app.open` → `ui.tap` → `ui.scroll` → `device.back` | Las acciones semánticas recorren Settings sin coordenadas del modelo. | Paquete foreground, selector devuelto y una evidencia por acción. |
| FLOW-TEXT-1 | `app.open` → `ui.tap` → `ui.type_text` | El texto llega a un campo Android real por selector semántico. | Conteo de caracteres, árbol posterior y PNG. |
| FLOW-APP-1 | `app.open(package)` → `ui.get_tree` | Un paquete lanzable declarado se abre y queda observable. | Paquete foreground y PNG; requiere `ANDROID_MCP_ECA_TARGET_PACKAGE`. |

## Campaña v1

1. Ejecutar el banco unitario: `python -m unittest discover -s tests -v`.
2. Con AVD y Appium levantados, ejecutar la campaña real:

   ```powershell
   $env:ANDROID_MCP_RUN_EMULATOR = '1'
   .\.venv\Scripts\python -m unittest tests.test_mcp_emulator_e2e -v
   ```

3. Registrar los resultados y cualquier hallazgo en este documento o en una
   regresión nueva. No cambiar este oráculo para convertir un fallo en verde.

## Límites actuales

- Cubre la puerta MCP, observación ADB, navegación Settings y el transporte
  stdio local.
- No valida todavía una aplicación Android propia ni interacción con Trinidad,
  Auralis o Glas. Esas integraciones serán clientes externos de esta misma
  frontera, no autoridad adicional.

## Resultados v1.1 (Android 16)

- `FLOW-NAV-1` llega al marcador observable `All apps` mediante la intención
  fija `android.settings.APPLICATION_SETTINGS`.
- `FLOW-UI-1` comprueba tocar, desplazar y volver sin coordenadas de entrada.
- `FLOW-TEXT-1` usa `input_hint: "Search"` para escribir en el `EditText` real
  que Android 16 no expone con `resource-id`.
