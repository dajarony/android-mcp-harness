# Android MCP Harness

Harness local para observar y controlar un emulador Android mediante Appium,
UiAutomator2 y ADB. El objetivo inicial es demostrar la cadena completa:

```text
Python → Appium → UiAutomator2 → ADB → Android Emulator
```

## Estado actual

Fase 1: demo segura que abre Ajustes, localiza `Apps`, pulsa el elemento y guarda
una captura en `artifacts/`.

No incluye MCP, agentes, Auralis, Trinidad ni Glas todavía.

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
