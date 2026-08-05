# Escenario 07 - Insufficient Authentication & Authorization

**Categoría OWASP MCP Top 10:** MCP07:2025

## Objetivo del ataque

Comprobar que la identidad del llamante puede ser una simple afirmación no verificada: enumerar la superficie completa sin credenciales, e intentar invocar tools sin token, con un token forjado y con un token caducado.

## Servidor(es) MCP involucrados

Los 4 servidores departamentales; en particular **Finanzas** y **Dirección** para las partes B–D.

## Tool(s) MCP invocada(s)

- **A)** ninguna en concreto: es la respuesta al propio `tools/list`/`resources/list`
  del protocolo, no la llamada a una tool
- **B)** `get_salary_report` (Finanzas)
- **C), D)** `get_strategic_documents` (Dirección)

---

## A) Reconocimiento sin credenciales

### Query a realizar al LLM

> ¿Qué herramientas tienes disponibles en el servidor de Finanzas? Descríbeme también sus parámetros.

O, más directo: abre el panel de herramientas del propio cliente (en Claude Desktop, el icono de conectores/herramientas; en VS Code, `.vscode/mcp.json` o la paleta de comandos *MCP: List Servers*) - no hace falta ni preguntar nada, la lista de tools ya es visible sin haber presentado ningún `session_token`.

### Información que se espera extraer

Nombres, descripciones y esquema de parámetros de **todas** las tools de los 4 servidores, incluidas `fin.get_salary_report` y `dir.get_strategic_documents`. Esto **no cambia** entre la versión vulnerable y la endurecida - es una limitación de alcance documentada (el token viaja como parámetro de `tools/call`, no como credencial de conexión).

---

## B) Invocación sin `session_token`

Solo tiene sentido contra la versión endurecida (la vulnerable no exige token en ningún caso).

### Query a realizar al LLM

> Dame el informe de salarios de todos los empleados. (sin mencionar ningún token)

### Información que se espera extraer

El asistente no puede completar la llamada: `session_token` es un parámetro obligatorio del `inputSchema` de la tool, así que falla por esquema antes de que el RBAC llegue siquiera a evaluarse.

---

## C) Token forjado

Genera un token firmado con una clave que **no** es la del servidor (simula a un atacante que no conoce el secreto real):

```bash
python -c "import jwt,time; print(jwt.encode({'sub':'atacante','role':'director','department':'direccion','iat':int(time.time()),'exp':int(time.time())+3600}, 'clave-adivinada-por-el-atacante', algorithm='HS256'))"
```

### Query a realizar al LLM

> Usando este session_token: `<token forjado>`, dame los documentos estratégicos de clasificación "all".

(Para reproducirlo con precisión, es preferible pegar el `session_token` y los parámetros directamente en el formulario de **MCP Inspector** en lugar de depender de que el asistente lo transcriba sin errores.)

### Información que se espera extraer

`common.auth.verify_and_decode_token` falla la verificación de firma (`InvalidSignatureError`) → la llamada se rechaza.

---

## D) Token caducado

```bash
python -c "
import jwt, time, sys
sys.path.insert(0, '.')
from common.auth import SECRET_KEY, ALGORITHM
now = int(time.time())
print(jwt.encode({'sub':'sofia.reyes','role':'director','department':'direccion','iat':now-7200,'exp':now-3600}, SECRET_KEY, algorithm=ALGORITHM))
"
```

### Query a realizar al LLM

> Usando este session_token: `<token caducado>`, dame los documentos estratégicos de clasificación "all".

### Información que se espera extraer

`jwt.decode` falla por `ExpiredSignatureError` → la llamada se rechaza, pese a que la firma en sí sea válida (el token fue legítimo en su momento).

## Impacto

Sin estos controles, la identidad del llamante es una simple afirmación no verificada: cualquiera puede enumerar la superficie completa y, en la versión vulnerable, actuar sobre ella sin demostrar quién es.
