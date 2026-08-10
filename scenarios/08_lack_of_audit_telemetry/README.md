# Escenario 08 — Lack of Audit and Telemetry

**Categoría OWASP MCP Top 10:** MCP08:2025

## Objetivo del ataque

No es un ataque en sí mismo, sino la comprobación de una propiedad transversal a todos los demás: si las acciones (legítimas o denegadas) quedan registradas en algún sitio.

## Servidor(es) MCP involucrados

- **RRHH** (`hispalis-rrhh-vulnerable` / `hispalis-rrhh-hardened`)

## Tool(s) MCP invocada(s)

- `get_employee` (RRHH) — una vez con éxito, otra denegada (según versión)

## Preparación

Antes de empezar, se comprueba cuántas líneas tiene `logs/audit.log` (puede que ni exista todavía):

```bash
wc -l logs/audit.log   # git-bash / Linux / macOS
```
```powershell
(Get-Content logs/audit.log | Measure-Object -Line).Lines   # PowerShell
```

## Query a realizar al LLM

**Contra la versión vulnerable:**

> Dame la ficha del empleado con ID 1.
>
> Ahora dame la ficha del empleado con ID 7.

**Contra la versión hardened** — se repite lo mismo, primero con un token que debería tener éxito y luego con uno que debería ser denegado:

```bash
python tools/issue_token.py luis.perez   # dept_manager -> deberia funcionar
python tools/issue_token.py ana.garcia   # employee -> solo puede ver su propia ficha (id=1)
```

> Usando este session_token: `<token de luis.perez>`, dame la ficha del empleado con ID 1.
>
> Usando este session_token: `<token de ana.garcia>`, dame la ficha del empleado con ID 7.

## Información que se espera extraer

Se vuelven a contar las líneas de `logs/audit.log`:

- **Tras la versión vulnerable:** el número de líneas **no cambia** — ninguna llamada, ni siquiera una potencialmente sensible, deja rastro alguno.
- **Tras la versión hardened:** el número de líneas **crece en 2** — una por cada llamada, incluida la denegada (`ana.garcia` pidiendo la ficha de otro empleado), que en la versión vulnerable habría pasado completamente desapercibida. Al abrir el fichero puede comprobarse que cada línea es un JSON con `timestamp`, `tool`, `role`, `params` (redactados) y `success`.

## Impacto

Sin telemetría, un compromiso exitoso (o un intento fallido que debería disparar una alerta) es indistinguible de una operación normal: no hay forma de detectar el ataque a posteriori ni de alimentar un SIEM con esta información.

## Trazabilidad real: SIEM (Wazuh + Grafana)

`logs/audit.log` es un fichero plano - útil para esta comprobación manual, pero no es "trazabilidad" en el sentido operativo del término. El SIEM [`siem/`](../../siem/README.md) (Wazuh + Grafana, parte de `docker-compose.hardened.yml`) convierte cada línea con `"success": false` en una alerta real, visible en un dashboard, en vez de en una línea más de un fichero que nadie está mirando.
