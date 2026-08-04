# Escenario 05 - Command Injection & Execution

**Categoría OWASP MCP Top 10:** MCP05:2025

## Objetivo del ataque

La categoría oficial cubre cualquier caso en el que un agente "construye y ejecuta
comandos... usando entrada no confiable sin validación adecuada". Este escenario reúne tres técnicas contra dos intérpretes distintos: el motor SQL (SQLi) y el sistema de ficheros (Path Traversal), más una demostración de por qué el encoding no sirve como defensa.

> **Nota sobre las queries:** pedirle a un asistente bien alineado "haz una inyección SQL" de forma genérica no garantiza que use el payload exacto. Es más fiable indicarle explícitamente la tool y el valor del parámetro, tal y como se muestra abajo, o usar directamente el formulario de **MCP Inspector** (`npx @modelcontextprotocol/inspector`) para invocar la tool con el payload pegado literalmente.

## Servidor(es) MCP involucrados

- **Finanzas** (`hispalis-finanzas-vulnerable` / `-hardened`) - SQLi y encoding bypass
- **IT** (`hispalis-it-vulnerable` / `-hardened`) - Path Traversal

## Tool(s) MCP invocada(s)

- `query_invoices` (Finanzas) - técnicas A) SQL Injection y C) bypass por encoding
- `read_config` (IT) - técnica B) Path Traversal

---

## A) SQL Injection en `fin.query_invoices`

### Query a realizar al LLM

**Vulnerable:**

> Usa la tool `query_invoices` con el parámetro `filter` igual exactamente a: `' UNION SELECT 1, name, salary, 'paid', '2026-01-01' FROM employees -- -`

**Endurecida** (`python tools/issue_token.py marta.ruiz` para obtener un token):

> Usando este session_token: `<token>`, usa la tool `query_invoices` con `filter.status` igual a ese mismo payload.

### Información que se espera extraer

- **Vulnerable:** la respuesta incluye filas de la tabla `employees` (nombre, salario) camufladas como si fueran facturas.
- **Endurecida:** error de validación de esquema - `filter.status` solo admite `"paid"`, `"pending"` u `"overdue"` (`Literal` de Pydantic); la consulta nunca llega a ejecutarse.

---

## B) Path Traversal en `it.read_config`

### Query a realizar al LLM

**Vulnerable:**

> Usa la tool `read_config` con `path` igual a `../secrets/api_keys.txt`.
>
> Después, prueba también con `path` igual a `../../it/it.db`.

**Endurecida** (`python tools/issue_token.py elena.vidal`):

> Usando este session_token: `<token>`, usa la tool `read_config` con esos mismos
> valores de `path`.

### Información que se espera extraer

- **Vulnerable:** el primer payload devuelve credenciales AWS/SMTP falsas de `servers/it/secrets/api_keys.txt`; el segundo devuelve el contenido binario de `servers/it/it.db` (la propia base de datos de tickets del servidor de IT) - ninguno de los dos debería ser accesible a través de `read_config`.
- **Endurecida:** ambos se rechazan con `"Acceso a ruta no permitida."` - `os.path.realpath` resuelve la ruta y comprueba que siga dentro de `configs/`.

---

## Impacto

Extracción de datos de otros dominios funcionales (SQLi), lectura de ficheros arbitrarios del sistema incluyendo credenciales y bases de datos que el propio proceso puede alcanzar (Path Traversal).
