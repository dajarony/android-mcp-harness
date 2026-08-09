# SUME + STDG — Android MCP Harness

Este proyecto usa **SUME + STDG** para separar responsabilidades y mantener
trazabilidad de cada cambio.

| Carpeta | Responsabilidad |
|---|---|
| `entradas/` | Comandos locales y futuras entradas MCP |
| `logica/` | Sesiones, navegación, controladores y evidencia |
| `salidas/` | Formatos de respuesta para consumidores |
| `contratos/` | Datos que se cruzan entre capas |
| `cambios/` | Historial append-only de modificaciones |
| `mapa-global/` | Mapa vivo de dependencias y flujos |

Antes de cambiar una pieza, revisa `mapa-global/arquitectura.yaml`. Cada archivo
en las cuatro capas principales comienza con un **SUME DOCBLOCK** y hace una
sola cosa.
