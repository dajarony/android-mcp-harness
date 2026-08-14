# Cliente MCP de referencia

## Definición

Cliente externo por stdio que prueba una tarea declarada contra el catálogo MCP
real. No interpreta XML, no genera selectores, no abre puertos y no gana ninguna
autoridad distinta de las doce herramientas del arnés.

## Entradas

Un JSON con `package_name` y una lista no vacía de pasos. Cada paso contiene
solamente `ui.tap`, `ui.type_text`, `ui.scroll` o `device.back`, con argumentos
del contrato público. El cliente rechaza un `session_id` en el JSON: ese token lo
crea y lo destruye el propio cliente.

## Flujo

1. Llama `app.open(package_name)`.
2. Observa `ui.get_tree` inicial.
3. Abre `ui.session.open`.
4. Ejecuta cada paso declarado con ese `session_id`.
5. Cierra la sesión en `finally`, incluso si un paso falla.
6. Observa `ui.get_tree` final y emite un informe JSON.

## Resultado y errores

El informe conserva cada respuesta MCP, incluida su evidencia. Ante el primer
error de una acción deja de ejecutar la receta, cierra la sesión y devuelve ese
error tipado; no intenta un toque alternativo ni un selector inventado.

## Verificación

`tests/test_reference_client.py` comprueba el orden de transporte, que el token
no se puede aportar desde el archivo y que el cierre ocurre después de un fallo.
