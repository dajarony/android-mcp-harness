# Registro de cambios — android-mcp-harness

Este archivo resume cambios técnicos relevantes del proyecto. Los detalles internos del proceso de desarrollo no forman parte de la documentación pública.

## 0.8.0 — 2026-08-14

- Catálogo MCP estabilizado en doce herramientas declaradas.
- Sesiones UI reutilizables con caducidad y cierre explícito.
- Límite temporal para llamadas Appium que retienen el emulador.
- Separación interna del resumen de pantalla y del ejecutor de acciones UI.
- Selectores semánticos con contexto `within` para desambiguación.
- Compatibilidad verificada con Android API 34 y API 36.
- Flujo de referencia contra una aplicación Android real.
- Documentación de arquitectura alineada con los límites de módulos.

## 0.7.x — 2026-08-14

- Mejoras de diagnóstico del entorno con `doctor`.
- Detección de elementos cubiertos por el teclado.
- Soporte de etiquetas accesibles con saltos de línea.
- Evidencia de captura validada para rechazar imágenes planas o inválidas.
- Comprobaciones para mantener sincronizados el catálogo MCP, los validadores y la documentación pública.

## 0.6.x — 2026-08-13

- Guardias de seguridad aplicados a todas las rutas que pueden abrir una sesión.
- Restricción explícita a emuladores Android y Appium local.
- Errores tipados y respuestas normalizadas en toda la superficie MCP.

## 0.5.x y anteriores

- Servidor MCP local por stdio.
- Observación Android mediante ADB de solo lectura.
- Navegación semántica sin coordenadas de entrada.
- Evidencia PNG por operación.
- Contratos FASER, oráculo ECA y pruebas unitarias/E2E para las capacidades publicadas.

Para conocer el estado actual, límites, instalación y verificación, consulta `README.md` y `docs/`.
