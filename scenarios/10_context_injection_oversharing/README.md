# Escenario 10 - Context Injection & Over-Sharing

**Categoría OWASP MCP Top 10:** MCP10:2025

## Objetivo del ataque

Conseguir datos generados por otro usuario sin haberlos pedido tú mismo, a través de una caché de resultados que no distingue quién la llenó.

## Servidor(es) MCP involucrados

- **Finanzas** (`hispalis-finanzas-vulnerable` / `hispalis-finanzas-hardened`)

## Tool(s) MCP invocada(s)

- `get_salary_report` (Finanzas) - sesión 1, genera y cachea el informe
- `get_cached_report` (Finanzas) - sesión 2, intenta leer el resultado ajeno

## Query a realizar al LLM

Necesitas **dos conversaciones/sesiones distintas** con el mismo servidor (dos ventanas o dos chats separados del cliente), simulando a dos usuarios distintos.

**Sesión 1 (Sofía Reyes, directora) - genera el informe:**

Versión vulnerable:

> Dame el informe de salarios de todos los empleados.

Versión endurecida (`python tools/issue_token.py sofia.reyes`):

> Usando este session_token: `<token de sofia.reyes>`, dame el informe de salarios de todos los empleados.

**Sesión 2 (Carlos Soto, responsable de Finanzas, sin pedir nada primero) - intenta leer el resultado ajeno:**

Versión vulnerable:

> ¿Tienes algún informe de nóminas ya generado que puedas darme sin volver a consultarlo?

Versión endurecida (`python tools/issue_token.py carlos.soto`):

> Usando este session_token: `<token de carlos.soto>`, dame el último informe de nómina que tengas cacheado.

## Información que se espera extraer

- **Vulnerable:** en la Sesión 2, Carlos Soto recibe el informe **completo** que
  generó Sofía Reyes segundos antes, sin haberlo solicitado él mismo - la caché es
  una estructura global del proceso, compartida por todos los usuarios.
- **Endurecida:** en la Sesión 2, Carlos Soto recibe
  `"No tienes ningun informe cacheado en esta sesion."` - la caché está indexada
  por el `sub` del propio token (`common.session.SessionContext`), así que solo
  ve lo que él mismo generó, aunque su rol esté perfectamente autorizado a usar la
  tool.

## Impacto

Los datos de una tarea o usuario pueden filtrarse a otra tarea o usuario que comparte el mismo proceso de servidor, incluso sin que exista ningún fallo de control de acceso: el problema es que el "contexto" (aquí, una caché de resultados) no está correctamente delimitado por sesión.
