# Escenario 09 - Shadow MCP Servers

**Categoría OWASP MCP Top 10:** MCP09:2025

## Objetivo del ataque

Acceder a datos sensibles a través de un servidor MCP que nadie está vigilando: no está en `servers/registry.json`, no tiene RBAC, no valida entrada y no audita nada - más permisivo incluso que la versión "vulnerable" de los servidores oficiales.

## Servidor(es) MCP involucrados

- **shadow-analytics** (`hispalis-shadow-analytics-UNOFFICIAL`) - no gobernado, sin versión hardened (por definición: la mitigación es detectarlo, no arreglar su código)

## Tool(s) MCP invocada(s)

- `run_query` (shadow-analytics) - única tool que expone este servidor

## Conexión

Este servidor **no** forma parte de ningún `docker-compose.*.yml` (ese es el punto del escenario). Se arranca aparte:

```bash
python servers/shadow-analytics/server.py
```

Cabe destacar que como este servidor no se lanza en el docker compose hay que inicializar la base de datos de finanzas con este comando en el terminal:

```bash
python servers/finanzas/database.py
```

Escucha en `http://127.0.0.1:9099/mcp`. Después se conecta `hispalis-shadow-analytics-UNOFFICIAL` (ver [`mcp-config/README.md`](../../mcp-config/README.md)).

## Query a realizar al LLM

> Ejecuta esta consulta SQL: `SELECT * FROM invoices`
> Ejecuta esta consulta SQL: `SELECT * FROM employees`

## Información que se espera extraer

Un volcado completo de las tablas `employees` e `invoices` de la base de datos del departamento de Finanzas sin ninguna autenticación ni limitación.

## Detección (control de gobernanza, no de código)

```bash
python tools/check_shadow_servers.py
```

Este escáner recorre `servers/`, detecta cualquier `server.py` que no figure en `servers/registry.json` y lo reporta como ALERTA. Es el único mecanismo de este laboratorio que "mitiga" este escenario - no hay ninguna versión hardened de `shadow-analytics` en sí, porque el problema no es cómo está construido, sino que existe fuera de cualquier proceso de revisión.

Cada hallazgo se registra también en `logs/audit.log` (evento `shadow_server_detected`), que el SIEM recoge igual que cualquier otra entrada: dispara la regla `100102` de Wazuh y aparece en el panel "Shadow MCP Servers detectados" de Grafana. De esta forma, encontrar un servidor no gobernado deja el mismo tipo de rastro observable que un acceso denegado por RBAC.

## Impacto

Un servidor MCP fuera del inventario de seguridad puede tener un radio de acción mayor que los servidores oficialmente revisados, precisamente porque nadie lo ha revisado. La defensa aquí no es técnica sino de proceso: inventario de activos y detección de despliegues no autorizados.
