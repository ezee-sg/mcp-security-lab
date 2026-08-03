# servers/

Cuatro servidores MCP departamentales, cada uno en versión `server.py`
(vulnerable) y `server_hardened.py` (endurecida), más `shadow-analytics/`
(servidor no gobernado, fuera de Docker y de `registry.json`).

| Departamento | Tools | Vulnerabilidad (`server.py`) | Control (`server_hardened.py`) | Escenario(s) |
|---|---|---|---|---|
| RRHH | `get_employee`, `list_employees` | Sin RBAC; descripción de `get_employee` cargada desde `descriptions.json` (envenenable) | `require_role` + "solo lectura propia" para `employee` | 03, 08 |
| Finanzas | `query_invoices`, `get_salary_report`, `get_cached_report` | SQL Injection por concatenación; sin RBAC; caché global sin aislar por sesión | Pydantic + consultas parametrizadas; RBAC; caché por sesión (`SessionContext`) | 02, 04, 05, 10 |
| IT | `read_config`, `send_notification`, `create_ticket` | Path Traversal; credenciales en texto plano; resource sin sanitizar; notificaciones sin whitelist | Canonicalización + whitelist de rutas; `redact_secrets`; `sanitize_untrusted_text`; whitelist de destinos + HITL | 01, 03, 05, 06 |
| Dirección | `get_strategic_documents` | Sin RBAC | `require_role("director")` exclusivamente | 03 |
| shadow-analytics | `run_query` | Sin RBAC, sin validación, SQL arbitrario contra `finanzas.db` | *(no tiene versión endurecida ya que la mitigación es de gobernanza, ver `tools/check_shadow_servers.py`)* | 09 |
