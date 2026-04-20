# Logs de errores al probar el MCP (UEFN)

Fecha: 2026-04-20

Este documento recopila errores observados durante pruebas de integración entre OpenCode (cliente MCP) y el listener de UEFN, con el objetivo de que el agente de desarrollo del MCP pueda reproducirlos y mejorar validaciones/mensajes.

---

## Error 1 — Disallowed reference a `TextRenderActor`

### Evidencia (mensaje observado)

```
/pruebasfutbol/minijuego_mcp.minijuego_mcp:PersistentLevel.TextRenderActor_UAID_D8BBC193BEE465D302_1960972099
     /pruebasfutbol/minijuego_mcp.minijuego_mcp:PersistentLevel.TextRenderActor_UAID_D8BBC193BEE465D302_1960961098
     /pruebasfutbol/minijuego_mcp.minijuego_mcp:PersistentLevel.TextRenderActor_UAID_D8BBC193BEE465D302_1960984100
     /pruebasfutbol/minijuego_mcp.minijuego_mcp:PersistentLevel.TextRenderActor_UAID_D8BBC193BEE464D302_1760145913
     /pruebasfutbol/minijuego_mcp.minijuego_mcp:PersistentLevel.TextRenderActor_UAID_D8BBC193BEE465D302_1960994101
     /pruebasfutbol/minijuego_mcp.minijuego_mcp:PersistentLevel.TextRenderActor_UAID_D8BBC193BEE465D302_1967282102
     /pruebasfutbol/minijuego_mcp.minijuego_mcp:PersistentLevel.TextRenderActor_UAID_D8BBC193BEE465D302_1960949097
Disallowed reference to /Script/Engine.TextRenderActor, Referenced by: See below for asset list, Plugin: pruebasfutbol.
```

### Qué significa (interpretación)

UEFN/Creative bloquea (por políticas de contenido) referencias a ciertas clases de Unreal Engine “no permitidas” dentro de un proyecto/isla (en este caso `Engine.TextRenderActor`). El error lista instancias en el nivel (`PersistentLevel`) que están referenciando esa clase.

### Impacto

- La isla/proyecto queda en estado inválido respecto a las reglas de UEFN.
- Según el flujo, puede impedir validaciones, sesiones, publicación o guardados/chequeos de contenido.

### Posible disparador durante pruebas del MCP

- Alguna acción del MCP habría creado o referenciado actores `TextRenderActor` (por ejemplo, vía una tool tipo `spawn_actor` usando `actor_class="TextRenderActor"`, o mediante `execute_python` que instancie/duplique ese actor).

> Nota: no se adjuntaron aún los pasos exactos ni el comando/tool que lo disparó; conviene capturarlos en la próxima iteración (ver “Datos faltantes”).

### Datos faltantes para reproducibilidad (pedir/registrar)

- Tool/endpoint exacto usado (p.ej. `spawn_actor`, `execute_python`, otra).
- Input completo enviado (clase/asset_path, transform, etc.).
- Momento en que aparece el error (al spawn, al guardar, al validar, al lanzar sesión, etc.).
- Output del listener y/o Output Log de UEFN alrededor del evento.

### Recomendación técnica (producto / MCP)

1. **Validación previa en el MCP** para evitar generar contenido inválido:
   - Implementar una **denylist/allowlist configurable** de clases/actores spawneables en UEFN (por defecto conservadora).
   - Si el usuario pide algo bloqueado (p.ej. `TextRenderActor`), responder con error estructurado: `code: "disallowed_actor_class"` y un mensaje corto.

2. **Ergonomía**:
   - Sugerir alternativas “UEFN-friendly” a nivel conceptual (sin prometer clases específicas si no están verificadas), por ejemplo: usar dispositivos/soluciones permitidas para mostrar texto en juego en lugar de un `TextRenderActor`.

3. **Observabilidad**:
   - Registrar en logs del servidor MCP: tool invocada + parámetros (sanitizados) + correlación con respuesta del listener.

---

## Próximos errores

Pegá abajo nuevos errores (ideal: stacktrace + tool + inputs + pasos de repro) y se agregan como secciones `Error N`.
