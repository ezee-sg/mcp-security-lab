# tools/

Utilidades de línea de comandos que apoyan el laboratorio. Ninguna automatiza un ataque: representan lo que en una organización real serían controles de proceso (escaneo pre-deploy, gestión de inventario) o pasos de infraestructura de pruebas (login, generación de lockfiles).

| Script | Para qué sirve |
|---|---|
| `issue_token.py` | CLI de login: emite un `session_token` (JWT) válido para un usuario del laboratorio (`python tools/issue_token.py <usuario>`). Sustituye el paso de autenticación que haría el host MCP; el token resultante se pega manualmente en el chat o en MCP Inspector al probar las versiones endurecidas. |
| `mcp_scan_lite.py` | Analizador estático de `descriptions.json`: busca patrones típicos de instrucciones ocultas dirigidas al modelo (`[OCULTO...]`, "ignora la solicitud", etc.). Reimplementación mínima de un escáner tipo MCP-Scan — mitigación de **Tool Poisoning (MCP03:2025)**, pensada para ejecutarse antes de cada despliegue. |
| `generate_lockfile.py` | Calcula el hash SHA-256 de las dependencias "vendorizadas" (p. ej. `servers/finanzas/vendor/report_formatter.py`) y lo guarda en su `dependencies.lock.json`. Fija la línea base de integridad — ejecutar tras clonar el repo y cada vez que esa dependencia cambie de forma legítima. |
| `verify_dependencies.py` | Compara el hash actual de una dependencia vendorizada con el fijado en su lockfile. Mitigación de **Software Supply Chain Attacks (MCP04:2025)**: si no coinciden, el pipeline de despliegue debería abortar. |
| `check_shadow_servers.py` | Recorre `servers/`, detecta cualquier `server.py` que no figure en `servers/registry.json` y lo reporta (además de registrarlo en `logs/audit.log`, de donde lo recoge el SIEM — ver [`siem/README.md`](../siem/README.md)). Mitigación de **Shadow MCP Servers (MCP09:2025)** — es un control de gobernanza/inventario, no de código. |

## Cuándo usar cada uno

- Antes de la primera ejecución: `generate_lockfile.py` (una vez).
- Para probar cualquier escenario contra la versión endurecida: `issue_token.py`.
- Como parte del escenario `03_tool_poisoning`: `mcp_scan_lite.py`.
- Como parte del escenario `04_supply_chain_dependency_tampering`: `verify_dependencies.py`.
- Como parte del escenario `09_shadow_mcp_servers`: `check_shadow_servers.py`.

Todos aceptan `-h`/sin argumentos para mostrar su uso, y devuelven código de salida `0` si todo está en orden o `1`/`2` si detectan un problema o faltan argumentos — pensado para poder engancharlos a un pipeline CI/CD real sin cambios.
