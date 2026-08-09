# Android MCP Harness

> Arquitectura SUME + STDG activa: [mapa global](mapa-global/arquitectura.yaml),
> [registro de cambios](cambios/registro-cambios.md) y
> [guía de estructura](SUME-README.md).

El flujo ya no vive en un único script: entrada, contratos, sesión Appium,
navegación, evidencia y salida están separados para que el futuro MCP escale sin
mezclar responsabilidades.

Harness local para observar y controlar un emulador Android mediante Appium,
UiAutomator2 y ADB. El objetivo inicial es demostrar la cadena completa:

```text
Python → Appium → UiAutomator2 → ADB → Android Emulator
```

## Estado actual

Fase 1: demo segura que abre Ajustes, localiza `Apps`, pulsa el elemento y guarda
una captura en `artifacts/`.

No integra todavía agentes, Auralis, Trinidad ni Glas: serán clientes del MCP,
no una ampliación de autoridad sobre Android.

## Preparación local

1. Arrancar un emulador Android desde Android Studio.
2. Crear el entorno Python e instalar el cliente:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python -m pip install -r requirements.txt
   ```

3. En otra terminal, iniciar Appium:

   ```powershell
   $env:JAVA_HOME = 'C:\Program Files\Eclipse Adoptium\jdk-17.0.17.10-hotspot'
   $env:ANDROID_HOME = 'C:\Users\gatak\AppData\Local\Android\Sdk'
   $env:Path = "$env:JAVA_HOME\bin;$env:ANDROID_HOME\platform-tools;$env:Path"
   .\node_modules\.bin\appium.cmd
   ```

4. Ejecutar el demo:

   ```powershell
   .\.venv\Scripts\python scripts\demo_settings.py
   ```

El script solo se conecta al emulador `emulator-5554` salvo que se indique otro
valor mediante `ANDROID_UDID`.

## MCP local y campaña ECA

El arnés ya expone un servidor MCP local por **stdio**, sin abrir un puerto de
red. Sus cuatro herramientas son `emulator.get_status`, `ui.get_tree`,
`screen.capture` y `settings.open_apps`. Las tres primeras son observación; la
última es la única navegación declarada: Ajustes → Apps.

Un cliente MCP, como Trinidad en una fase posterior, debe iniciar este comando:

```powershell
.\.venv\Scripts\python -m entradas.mcp.server
```

Para comprobar el comportamiento con el AVD y Appium activos, ejecutar la
campaña ECA real:

```powershell
$env:ANDROID_MCP_RUN_EMULATOR = '1'
.\.venv\Scripts\python -m unittest tests.test_mcp_emulator_e2e -v
```

La campaña comprueba observación sin cambio de pantalla, navegación con
evidencia local y el protocolo stdio en un proceso separado.
