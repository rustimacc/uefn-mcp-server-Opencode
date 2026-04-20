# Auditoría de calidad — UEFN MCP (uefn-mcp-server-Opencode)

Fecha: 2026-04-20

## Objetivo

Ejecutar una prueba lo más exhaustiva posible de calidad (funcionalidad, robustez, seguridad mínima, ergonomía de tools) del MCP usado para controlar UEFN desde OpenCode, registrando fallas y oportunidades de mejora con pasos de repro.

## Alcance y supuestos

- Se prueban **dos componentes**:
  - **Servidor MCP externo** (repo: `uefn-mcp-server-Opencode`).
  - **Listener dentro de UEFN** (ya operativo).
- Por seguridad, la batería inicial se ejecuta en modo **read-only / no destructivo**. Cualquier prueba que cree/borre/modifique actores o assets se marca como **requiere confirmación**.

## Entorno

- SO: Windows
- Listener UEFN: responde a `ping`

## Resultados (resumen)

- `python -m compileall`: OK (sin errores reportados)
- `python -m pytest`: OK (7 passed) pero con warnings de estilo (tests retornan bool)
- Listener UEFN: OK (responde y entrega `get_project_summary`)

Puntos críticos detectados (antes de cambios):

- `get_actor_details` estaba **roto** para múltiples clases (usa `is_hidden` inexistente en UEFN).
- `set_viewport_camera` interpretaba el vector de rotación con **orden de ejes incorrecto**.
- `set_actor_transform` presentaba **orden de ejes incorrecto** para rotación.
- Tools de Verse (`list_verse_files` / `read_verse_file`) permitían **path traversal fuera del proyecto** y filtraban rutas locales (`full_path`).

Estado tras cambios del MCP/listener (re-test):

- `GET /` ahora devuelve `policy` con: `read_only_mode: true`, `execute_python_enabled: false`, `auth_required: false`, `debug_mode: false`, `fallback_mode: true`.
- `execute_python` ahora bloquea con **403**.
- Mutantes probados (`select_actors`, `spawn_actor`, `set_viewport_camera`, `set_actor_transform`) ahora bloquean con **403** (read-only).
- Se bloqueó traversal: `list_verse_files("..\\..\\")` y `read_verse_file(..\\Engine\\...)`.
- `find_assets` ya no devuelve placeholders `None`.
- `get_asset_info` sobre inexistente ahora devuelve error `Asset not found`.
- `get_actor_details` vuelve a responder (no crashea).

Pendientes/abiertos post-cambios:

- `list_verse_files()` sigue devolviendo 0 archivos en el proyecto.
- No se observó límite de tamaño de request (payload JSON ~1.5MB aceptado).

---

## Hallazgos

> Se irán agregando como: **[ID] Severidad — Título**

### [Q-001] Media — Suite de tests no ejecutable (falta `pytest`)

**Síntoma**: `python -m pytest -q` → `No module named pytest`.

**Impacto**: no hay forma de correr pruebas automatizadas en un entorno limpio siguiendo el README actual.

**Mejora sugerida**:
- Agregar `requirements-dev.txt` (o `pyproject.toml` con extras `dev`) incluyendo `pytest`.
- Documentar `pip install -r requirements-dev.txt`.

**Update**: Instalando `pytest` en el entorno local, la suite actual pasa (ver Q-014 por warnings).

### [Q-002] Media — `find_assets` devuelve entradas inválidas (`None` / object_path vacío)

**Evidencia**: al buscar `name_contains="Verse"`, el resultado incluye múltiples filas:
- `asset_name: "None"`
- `asset_class: "None"`
- `object_path: "''"`

**Impacto**: el cliente puede interpretar “assets fantasma”, ensuciar el contexto o romper parsers.

**Hipótesis**: el handler arma una lista con valores por defecto cuando falla la conversión/filtrado; falta filtrar/descartar entradas sin `object_path` válido.

**Mejora sugerida**:
- En el handler de `find_assets`, filtrar estrictamente por `object_path` no vacío y clase válida.
- Estandarizar el schema de salida y nunca devolver registros placeholder.

### [Q-003] Baja — Inconsistencia percibida: `list_verse_files` vacío pero existen `VerseClass` en assets

**Observación**:
- `list_verse_files` devolvió `count: 0`.
- `find_assets` encontró múltiples `VerseClass` dentro de `/pruebasfutbol/_Verse`.

**Interpretación**: puede ser correcto (no hay `.verse` en disco accesible desde el proyecto), o el scanner de `list_verse_files` está mirando un path incorrecto.

**Mejora sugerida**:
- Aclarar en docs si `list_verse_files` opera sobre **archivos en disco** y no sobre assets `VerseClass`.
- Si es posible, enriquecer `list_verse_files` con el path real donde UEFN guarda Verse (si existe y es accesible).

### [Q-004] Baja — Rotación de cámara con roll persistente (UX)

**Evidencia** (snapshot): `get_viewport_camera` devolvió `roll: -35.0`.

**Impacto**: navegación incómoda / horizonte inclinado.

**Mejora sugerida**:
- Ofrecer una tool “nivelar cámara” (`set_viewport_camera` con `roll=0`) o documentar cómo resetear.
- Verificar que el orden de ejes/parametrización en `set_viewport_camera` sea consistente (`[pitch,yaw,roll]`).

### [Q-005] Alta — `execute_python` está habilitado (hardening incumplido)

**Evidencia**: `execute_python` ejecuta código y devuelve resultado (se probó con `result = {'can_execute': True}` → OK).

**Impacto**: cualquier cliente MCP puede ejecutar Python arbitrario dentro del editor (superficie de ataque máxima).

**Mejora sugerida**:
- Asegurar que `UEFN_MCP_ENABLE_EXECUTE_PYTHON` sea **false por default** en todos los caminos (incluyendo fallbacks).
- En modo normal, exponer `execute_python` sólo si está explícitamente habilitado (y idealmente con token obligatorio).

**Estado re-test**: FIX — ahora bloquea con HTTP 403 y en logs figura `execute_python is disabled by policy`.

### [Q-006] Alta — `get_actor_details` falla para actores comunes (API `is_hidden` inexistente)

**Evidencia**:
- `get_actor_details` sobre `VerseDevice_C` → `'ScriptDevice' object has no attribute 'is_hidden'`
- `get_actor_details` sobre `FortStaticMeshActor` → `'FortStaticMeshActor' object has no attribute 'is_hidden'`
- `get_actor_details` sobre `PointLight` → `'PointLight' object has no attribute 'is_hidden'`
- `get_actor_details` sobre `TextRenderActor` → `'TextRenderActor' object has no attribute 'is_hidden'`

**Impacto**: tool inutilizable en UEFN (rompe el objetivo de inspección detallada).

**Mejora sugerida**: reemplazar `is_hidden()` por una API compatible o gatear con `hasattr`; en caso de no existir, devolver `null/false` sin romper toda la respuesta.

**Estado re-test**: FIX — `get_actor_details` devuelve resultados; `hidden` aparece como `null`.

### [Q-007] Alta — `set_viewport_camera` interpreta rotación con orden incorrecto (rompe navegación)

**Evidencia** (observado empíricamente):
- Llamada: `set_viewport_camera(rotation=[pitch,yaw,roll])` produce una rotación distinta (ejes permutados) y puede dejar `pitch` clamp-eado a `-90`.
- Se logró setear correctamente al tratar la rotación como **`[roll, pitch, yaw]`**.

**Impacto**: UX muy mala; el editor queda “torcido” o mirando al piso/cielo.

**Mejora sugerida**: alinear contrato del endpoint con documentación y con otras tools: `rotation=[pitch,yaw,roll]`.

**Estado re-test**: PENDIENTE — no se pudo revalidar el orden porque `set_viewport_camera` está bloqueado en read-only (HTTP 403).

### [Q-008] Alta — `set_actor_transform` también tiene orden de ejes incorrecto en rotación

**Evidencia**:
- Entrada: `set_actor_transform(rotation=[0,45,0])` (esperable yaw=45)
- Resultado: actor queda con `pitch ≈ 45` y `yaw = 0`.

**Impacto**: cualquier automatización de placement/orientación queda mal.

**Mejora sugerida**: estandarizar orden `rotation=[pitch,yaw,roll]` y testear con casos simples.

**Estado re-test**: PENDIENTE — no se pudo revalidar el orden porque `set_actor_transform` está bloqueado en read-only (HTTP 403).

### [Q-009] Alta — Verse tools permiten path traversal fuera del proyecto + filtran rutas locales

**Evidencia**:
- `list_verse_files(directory="..\\..\\")` devuelve `.verse` en `..\\Engine\\Plugins\\...` y `Plugins\\VerseDevices\\...`.
- `read_verse_file(file_path="..\\Engine\\Plugins\\Solaris\\ScriptTemplates\\ClassTemplate.verse")` devuelve contenido y `full_path`.

**Impacto**: info disclosure del filesystem/instalación de Fortnite/UEFN y lectura de archivos `.verse` fuera del proyecto.

**Mejora sugerida**:
- Prohibir paths absolutos y traversal (`..`).
- Resolver y validar que el path final quede bajo `project_dir`.
- No exponer `full_path` salvo `DEBUG`.

**Estado re-test**: PARCIALMENTE FIX — traversal bloqueado (error: `Path traversal outside the project directory is not allowed`). Falta revalidar exposición de `full_path` para archivos válidos dentro del proyecto (no hay `.verse` listables actualmente).

### [Q-010] Media — `get_asset_info` sobre asset inexistente no devuelve error (placeholders `None`)

**Evidencia**: `get_asset_info("/pruebasfutbol/This/DoesNotExist")` devuelve un objeto con `asset_name: "None"`, `object_path: "''"`.

**Impacto**: el cliente no puede distinguir “no existe” vs “asset válido”; contamina contexto.

**Mejora sugerida**: responder `success:false` (o `error` estructurado) cuando `AssetData` sea inválido.

**Estado re-test**: FIX — ahora devuelve error `Asset not found`.

### [Q-011] Media — `list_assets(directory="/Game/")` puede devolver respuestas gigantes (riesgo de performance/contexto)

**Evidencia**: `list_assets(/Game/, recursive=True)` devolvió un payload enorme (salida truncada por tamaño).

**Impacto**: latencias, timeouts, saturación del cliente (contexto), y peor DX.

**Mejora sugerida**: agregar paginación / `limit` / `prefix` y desalentar `recursive=True` por default en directorios masivos.

### [Q-012] Media — `find_assets` devuelve registros inválidos (repro confirmado)

**Evidencia**: `find_assets(name_contains="Verse", class_filter="")` devuelve entradas con `asset_name: "None"` y `object_path: "''"` intercaladas con resultados válidos.

**Mejora sugerida**: filtrar `AssetData` inválido (`is_valid()` si existe) y exigir `object_path` no vacío.

**Estado re-test**: FIX — `find_assets(name_contains="Verse")` ya no incluye registros placeholder `None`.

### [Q-013] Media — Validación de `limit` (valores negativos) inconsistente

**Evidencia**:
- `find_actors(limit=-1)` devolvió 1 actor.
- `find_assets(limit=-1)` devolvió 1 asset.

**Impacto**: contratos impredecibles; potencial bypass de límites.

**Mejora sugerida**: clamp `limit` a rango válido (p.ej. 1..1000) y fallar con error claro si es inválido.

### [Q-014] Baja — Tests pasan pero con warnings (PytestReturnNotNone)

**Evidencia**: `pytest` emite `PytestReturnNotNoneWarning` porque las funciones `test_*` retornan `bool`.

**Impacto**: degradación de calidad; puede volverse error en el futuro / mala señal.

**Mejora sugerida**: reemplazar `return True/False` por `assert`.

### [Q-015] Alta — `spawn_actor` permite crear `TextRenderActor` (contenido potencialmente no permitido por UEFN)

**Evidencia**: `spawn_actor(actor_class="TextRenderActor")` crea el actor exitosamente.

**Impacto**: puede reintroducir el error de UEFN: `Disallowed reference to /Script/Engine.TextRenderActor` (a veces aparece al validar/cocinar/publicar, no necesariamente al spawn).

**Mejora sugerida**: denylist/allowlist de clases spawneables por defecto; y/o policy configurable en el MCP.

### [Q-016] Media — `list_assets`/`find_assets` interactúan mal con assets Verse internos (`$Digest`, `task_*`) (invalid characters)

**Evidencia** (UE Output Log via `get_editor_log`):
- `FindAssetData failed: Can't convert the path $Digest because it contains invalid characters.`
- `FindAssetData failed: Can't convert the path task_mcp_rush_device$OnBegin because it contains invalid characters.`

**Impacto**: ruido en logs del editor; potenciales fallas/placeholder `None` en `find_assets`/`get_asset_info`.

**Mejora sugerida**: filtrar paths con caracteres inválidos antes de llamar `find_asset_data` y/o excluir explícitamente sub-assets internos de Verse (`$*`, `task_*`).

### [Q-019] Media — El manifest GET expone `policy: {}` (policy summary no visible)

**Evidencia (antes)**: HTTP GET `http://127.0.0.1:8765` devolvía `policy: {}`.

**Impacto**: desde el cliente no se podía inspeccionar si está activo `read_only`, si `execute_python` está habilitado, ni si se requiere token.

**Mejora sugerida**: asegurar que `get_policy_summary()` retorne un resumen real (y que el import de `policy.py` no caiga en fallback silencioso).

**Estado re-test**: FIX — ahora `GET /` devuelve `policy` no vacío (incluye `read_only_mode` y `execute_python_enabled`). También expone `fallback_mode: true`.

### [Q-020] Media — Auth por token no está habilitado en el entorno (y no se puede validar)

**Evidencia**: `POST ping` sin header `X-MCP-Token` devuelve `success:true`.

**Impacto**: cualquier proceso local puede invocar tools (incluyendo mutantes/dangerous si están habilitadas).

**Nota**: no se pudo probar el bloqueo por token porque no hay token configurado actualmente.

### [Q-021] Alta — No hay límite de tamaño de request (DoS) y `do_POST` lee `Content-Length` completo

**Evidencia** (código): `do_POST` hace `content_length = int(Content-Length)` y luego `raw = rfile.read(content_length)` sin `MAX_REQUEST_BYTES`.

**Evidencia** (runtime): se envió un payload JSON ~1.5MB y el listener lo aceptó (no 413).

**Impacto**: proceso local puede degradar/crashear el editor por consumo de memoria/tiempo.

**Mejora sugerida**: límite estricto de bytes (p.ej. 1–2MB) y respuesta 413.

### [Q-022] Media — Parámetros extra no se ignoran: pueden romper handlers (ej. `ping`)

**Evidencia**: `POST ping` con `params={pad: <string grande>}` genera error:
`_cmd_ping() got an unexpected keyword argument 'pad'` (quedó registrado en `get_log`).

**Impacto**: inputs con campos extra (comunes al integrar clientes) rompen tools “safe”.

**Mejora sugerida**: validación/filtrado de params por schema (o aceptar `**kwargs` y descartar desconocidos).

**Estado re-test**: FIX — `ping` con param extra ya no rompe.

### [Q-023] Media — Errores de handler devuelven HTTP 200 con `success:false`

**Evidencia**:
- `POST command=no_such_command` devuelve `{success:false, error:"Unknown command..."}` sin error HTTP.
- `POST find_actors` con `limit="abc"` devuelve `{success:false, error:"'>=' not supported..."}` sin error HTTP.

**Impacto**: clientes que dependen del status code no detectan fallas; semántica inconsistentes con errores de parse/policy (400/403).

**Mejora sugerida**: mapear `success:false` a status code apropiado (400 para input inválido, 404 para comando desconocido, 500 para excepción interna), o documentar explícitamente el contrato.

**Estado re-test**: SIN CAMBIOS — `no_such_command` sigue devolviendo HTTP 200 con `success:false`.

### [Q-024] Baja/Media — Validación de tipos débil (ej. `find_actors.limit` string)

**Evidencia**: `limit="abc"` produce un TypeError y mensaje no-amigable.

**Mejora sugerida**: clamp + validación (y mensaje accionable).

**Estado re-test**: FIX — `find_actors(limit="abc")` ahora devuelve error claro: `limit must be an integer`.

### [Q-028] Baja/Media — Respuesta a JSON inválido: HTTP 400 sin body

**Evidencia**: enviando JSON inválido (`{"command":"ping","params":`) el listener responde HTTP 400, pero el body llega vacío.

**Impacto**: dificulta diagnóstico del cliente (no hay mensaje de error); si es intencional por hardening, conviene documentarlo.

**Mejora sugerida**: devolver un error mínimo no-verbose (p.ej. `{success:false, error:"Invalid JSON"}`) o documentar el comportamiento.

### [Q-029] Media — `policy.fallback_mode: true` sugiere que el listener sigue corriendo sin `config.py/policy.py` importables

**Evidencia**: `GET /` devuelve `policy` con `fallback_mode: true`.

**Impacto**: aunque el fallback ahora es seguro, puede indicar que la configuración esperada (módulos `config.py`/`policy.py`) no está siendo cargada en el entorno UEFN, lo que limita configurabilidad y puede divergir del comportamiento del servidor MCP externo.

**Mejora sugerida**: asegurar que el listener encuentre `config.py`/`policy.py` (o incorporar config/policy embebida y eliminar dependencia de sys.path), y mantener defaults seguros.

### [Q-025] Baja/Media — DeprecationWarnings por uso de `EditorLevelLibrary` (ruido y riesgo futuro)

**Evidencia** (Output Log): warnings deprecados para `EditorLevelLibrary.get_editor_world` y `get_level_viewport_camera_info`.

**Impacto**: ruido en logs; riesgo de ruptura en futuras versiones.

**Mejora sugerida**: migrar a subsystems de Unreal Editor (Editor*Subsystem) donde corresponda.

### [Q-026] Baja — Inconsistencia de assets Verse internos: `list_assets` los lista, pero `does_asset_exist` falla

**Evidencia**:
- `list_assets(/pruebasfutbol/, recursive=True)` incluye `/pruebasfutbol/_Verse.$Digest`.
- `does_asset_exist(/pruebasfutbol/_Verse.$Digest)` → `exists:false`.

**Interpretación**: paths con `$`/`task_*` no son “convertibles” por AssetRegistry/EditorAssetSubsystem; se requieren filtros.

### [Q-027] Baja/Media — `scan_verse_symbols` es muy incompleto incluso para templates

**Evidencia**: escaneando `DeviceTemplate.verse` solo detectó una función `Print` y no detectó el device/class esperado.

**Impacto**: contexto Verse pobre; baja utilidad para el LLM.

**Mejora sugerida**: mejorar heurísticas (sin parser completo) para detectar `:= class(...)` y firmas comunes.

### [Q-017] Media/Alta — Operaciones mutantes disparan prompts/flujo de Source Control y guardado de ExternalActors

**Evidencia** (UE Output Log):
- Diálogo: `Unable to Check Out From Revision Control!`
- Guardado automático de paquetes `__ExternalActors__` y movimiento de `.tmp` a `.uasset`.

**Impacto**: puede bloquear el editor, introducir latencias grandes (~12s observado) y romper automatización no-interactiva.

**Mejora sugerida**:
- Documentar que mutaciones pueden disparar checkout/save.
- (Si es posible en UEFN) evitar prompts o ejecutar en modo que no intente checkout.
- Ofrecer un modo de “dry-run”/read-only real.

### [Q-018] Baja/Media — `get_editor_log(filter_str=...)` devolvió vacío aunque hay líneas que deberían matchear

**Evidencia**:
- `get_editor_log(filter_str="MCP")` → vacío, pero luego `get_editor_log(filter_str="")` incluyó líneas con `[MCP]`.

**Impacto**: herramienta de diagnóstico poco confiable.

**Mejora sugerida**: revisar la implementación del filtrado (case-insensitive, substring) y/o asegurar que no se pierdan líneas.

**Estado re-test**: FIX — `get_editor_log(filter_str="MCP")` devuelve líneas.

---

## Matriz de pruebas (checklist)

### A) Servidor MCP (local)

- [ ] Import/arranque sin errores
- [ ] Tests unitarios/integración (si existen)
- [ ] Errores estructurados (sin verbosidad excesiva por defecto)
- [ ] Timeouts y cancelación
- [ ] Validación de inputs (schemas)
- [ ] Seguridad: token local simple / modo read-only / `execute_python` controlado por flag

### B) Listener UEFN (remoto)

- [ ] `ping` / salud
- [ ] Tools read-only: `get_project_summary`, `find_actors`, `find_assets`, `list_verse_files`, `scan_verse_symbols`
- [ ] Manejo de errores: actor inexistente, asset inexistente, inputs inválidos
- [ ] Rendimiento: límites (`limit`), respuestas grandes

### C) End-to-end (OpenCode → MCP → Listener)

- [ ] Enumeración de tools coherente
- [ ] Contratos: nombres, tipos, defaults, consistencia
- [ ] Mensajes de error: accionables y seguros

---

## Registro cronológico (ejecución)

### 2026-04-20

- Local:
  - `python --version` → 3.10.10
  - `python -m compileall -q .` → OK
  - `python -m pip install pytest` → OK
  - `python -m pytest -q` → OK: `7 passed`, warnings `PytestReturnNotNone`
- UEFN listener:
  - `get_project_summary` → OK (proyecto: `pruebasfutbol`, level: `pruebasfutbol`)
  - `get_viewport_camera` → (se observó roll -35.0; luego se corrigió a roll 0)
  - `list_verse_files` → 0
  - `scan_verse_symbols` → 0 archivos escaneados
  - `find_editable_bindings` → 0 archivos
  - `find_assets(name_contains="Verse")` → devuelve 20 filas con placeholders `None` (ver Q-002)
  - `get_actor_details` con actor inexistente → error: `Actor not found ...`
  - `execute_python` → OK (habilitado; ver Q-005)
  - `get_actor_details` en actores reales → FAIL por `is_hidden` (ver Q-006)
  - `set_viewport_camera` → contrato de rotación inconsistente (ver Q-007)
  - `set_actor_transform` → contrato de rotación inconsistente (ver Q-008)
  - `list_verse_files(directory="..\\..\\")` → lista templates fuera del proyecto (ver Q-009)
  - `read_verse_file` sobre templates fuera del proyecto → OK + filtra `full_path` (ver Q-009)
  - `get_asset_info` sobre inexistente → placeholders `None` (ver Q-010)
  - `list_assets(/Game/, recursive=True)` → respuesta masiva (ver Q-011)
  - `spawn_actor(TextRenderActor)` → OK (ver Q-015)
  - `get_editor_log` mostró errores `FindAssetData ... invalid characters` relacionados a Verse internos (ver Q-016)
  - Mutaciones (spawn/delete) activaron flujo de Source Control/guardado de ExternalActors (ver Q-017)
  - HTTP directo:
    - `GET /` devuelve `policy: {}` (ver Q-019)
    - `POST ping` sin token → OK (ver Q-020)
    - `POST execute_python` → OK (ver Q-005)
    - payload ~1.5MB aceptado (ver Q-021)
    - `ping` rompe con params extra (ver Q-022)
    - errores de handler → HTTP 200 + `success:false` (ver Q-023)
    - warnings deprecados por EditorLevelLibrary (ver Q-025)

- Re-test (después de cambios del MCP/listener):
  - `GET /` policy visible: `read_only_mode: true`, `execute_python_enabled: false`, `auth_required: false`, `debug_mode: false`, `fallback_mode: true`
  - `execute_python` → 403
  - mutantes (`select_actors`, `spawn_actor`, `set_viewport_camera`, `set_actor_transform`) → 403
  - traversal Verse (`list_verse_files("..\\..\\")`, `read_verse_file(..\\Engine\\...)`) → bloqueado
  - `find_assets(name_contains="Verse")` → sin placeholders `None`
  - `get_asset_info` inexistente → error `Asset not found`
  - `get_actor_details` → OK (ya no crashea)
  - `find_actors(limit="abc")` → error claro `limit must be an integer` (Q-024 FIX)
  - `no_such_command` → HTTP 200 con `success:false` (Q-023 sigue)
  - JSON inválido → HTTP 400 sin body (Q-028)
