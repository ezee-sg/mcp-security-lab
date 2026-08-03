# common/

Módulos compartidos usados **únicamente** por las versiones endurecidas
(`server_hardened.py`) de los servidores MCP. Ningún `server.py` vulnerable importa
nada de aquí — esa ausencia es intencionada y forma parte del propio contraste
vulnerable/endurecida del laboratorio.

## `auth.py` — identidad, tokens y RBAC

Emisión y verificación de tokens de sesión firmados (JWT), y el control de acceso
basado en roles.

- `USERS`: los 7 usuarios ficticios del laboratorio (usuario → rol, departamento,
  `employee_id`), consultados por `tools/issue_token.py <usuario>` para emitir el
  `session_token` que se usa manualmente en cada `scenarios/*/README.md`.
- `issue_token(username)`: emite un JWT firmado con `SECRET_KEY`, válido 8h
  (`TOKEN_TTL_SECONDS`). Simula la autenticación que en un despliegue real haría el
  host MCP antes de abrir sesión con cada servidor departamental.
- `verify_and_decode_token(session_token)`: valida firma y expiración; lanza
  `InvalidSessionToken` si el token falta, está caducado o manipulado.
- `require_role(session_token, *allowed_roles)`: punto de entrada que usan las
  tools endurecidas. Verifica el token y comprueba que el rol esté entre los
  permitidos; lanza `PermissionError` en caso contrario, o devuelve el payload
  decodificado (`sub`, `role`, `department`, `employee_id`).

  **Por qué es una función y no un decorador:** el snippet ilustrativo de la
  memoria (`06-defensa-hardening.tex`) muestra un decorador `@require_role(...)`.
  Aquí se invoca explícitamente como primera línea de cada tool en su lugar, porque
  un decorador que absorbiera `session_token` mediante `**kwargs` lo ocultaría del
  `inputSchema` que FastMCP expone al cliente MCP — y el cliente necesita saber que
  ese parámetro existe para poder enviarlo.

## `logging_utils.py` — auditoría estructurada

`log_tool_call(tool_name, params, user_role, result, success)` registra cada
invocación en dos sitios: por consola (vía `logging`, logger `hispalis.audit`) y en
`logs/audit.log` (una línea JSON por evento, con timestamp, tool, rol, parámetros
redactados y resultado).

`redact_sensitive(params)` enmascara con `***REDACTED***` cualquier parámetro cuya
clave esté en `SENSITIVE_KEYS` o contenga `token`, antes de que el evento se
registre.

El logger de consola escribe en **stderr** (comportamiento por defecto de
`logging.StreamHandler` cuando no se le indica `stream` explícitamente); con
`docker compose logs <servicio>` se ve igualmente, junto con la salida de
uvicorn. *(Nota histórica: cuando los servidores hablaban STDIO en vez de
Streamable HTTP, esto era además obligatorio — stdout estaba reservado al canal
JSON-RPC del protocolo y escribir logs ahí lo habría corrompido. Con HTTP ya no es
estrictamente necesario, pero se mantiene por higiene y para no mezclar logs con
la respuesta de las tools.)*

Es el único módulo de `common/` que usa la versión **vulnerable** también de forma
indirecta: su ausencia en `server.py` es precisamente lo que demuestra el escenario
`08_lack_of_audit_telemetry` (OWASP MCP08:2025).

`logs/audit.log` es también la fuente que consume el SIEM incluido en
`docker-compose.hardened.yml` (ver [`siem/README.md`](../siem/README.md)):
Wazuh lee directamente este fichero y genera una alerta por cada entrada con
`"success": false`.

## `sanitize.py` — neutralización de contenido no confiable

Dos funciones independientes, cada una mitigando una categoría OWASP distinta:

- `sanitize_untrusted_text(text)`: busca patrones típicos de instrucciones
  dirigidas al modelo (`_SUSPICIOUS_PATTERNS`: bloques `[INSTRUCCION...]`, "ignora
  la solicitud", "ignore previous instructions", etc.), los sustituye por
  `REDACTED_MARK`, y envuelve el resultado en un delimitador
  `<untrusted_external_data>` que dice explícitamente que ese contenido no debe
  interpretarse como instrucción. Usado en el resource `it://tickets/latest` de
  `servers/it/server_hardened.py` — mitigación de MCP06:2025 (Intent Flow
  Subversion).
- `redact_secrets(text)`: enmascara el valor de cualquier línea `clave: valor` (o
  `clave=valor`) cuya clave sugiera una credencial (`password`, `secret`,
  `api_key`, `token`, `access_key` — ver `_SECRET_LINE_PATTERN`). Usado en
  `it.read_config` de `servers/it/server_hardened.py` — mitigación de MCP01:2025
  (Token Mismanagement & Secret Exposure). El RBAC decide *quién* puede leer un
  fichero de configuración; esta función evita que, aun estando autorizado, las
  credenciales que contenga viajen en texto plano hacia el contexto del modelo.

## `session.py` — aislamiento de sesión

`SessionContext`: contenedor de estado por sesión (caché de resultados
`cache_set`/`cache_get`, ficheros temporales registrados con
`register_temp_file`), con `cleanup()` para destruir ese estado de forma
determinista al terminar la sesión.

`get_or_create_session(session_id, user_role)` / `end_session(session_id)`:
registro global (`_SESSIONS`) que asocia cada `session_id` con su
`SessionContext`.

Usado por `fin.get_salary_report` / `fin.get_cached_report`
(`servers/finanzas/server_hardened.py`) para que la caché de un informe quede
asociada al usuario que lo generó (`session_id = payload["sub"]`) en lugar de
compartirse globalmente entre todos los usuarios del proceso — mitigación de
MCP10:2025 (Context Injection & Over-Sharing). La versión vulnerable usa un
diccionario global sin esta separación; ver escenario
`10_context_injection_oversharing`.
