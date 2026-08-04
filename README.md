# Hispalis Technologies - Laboratorio vulnerable de Model Context Protocol (MCP)

Parte práctica del TFM *"Diseño y evaluación de seguridad en arquitecturas LLM
basadas en MCP"* para el Máster Universitario en Ciberseguridad de la Universidad de Málaga.

Simula una organización ficticia (**Hispalis Technologies**) con 4 servidores MCP
departamentales (RRHH, Finanzas, IT y Dirección ), cada uno disponible en una
**versión vulnerable** y una **versión endurecida**, más un servidor "shadow" no
gobernado. Sobre este entorno se ejecutan **10 escenarios de ataque, uno por cada
categoría del [OWASP MCP Top 10](https://owasp.org/www-project-mcp-top-10/)**.

El laboratorio se despliega con **dos ficheros Docker Compose independientes**
([`docker-compose.vulnerable.yml`](docker-compose.vulnerable.yml) y [`docker-compose.hardened.yml`](docker-compose.hardened.yml)), cada uno con sus 4 servidores departamentales y su propio `exfil-listener`, escuchando en HTTP y listos para conectar desde Claude Desktop, VS Code, etc. sin más pasos.

> ⚠️ Entorno de aprendizaje. No usar contra datos reales ni exponerlo en redes no
> controladas. Las credenciales, tokens y "secretos" de este repositorio son ficticios.

## Estructura del repositorio

```
common/                    Módulos compartidos únicamente por las versiones endurecidas
├── auth.py                Emisión/verificación de tokens de sesión (JWT) + RBAC (require_role)
├── logging_utils.py       Logging estructurado de invocaciones de tools (consola + logs/audit.log)
├── sanitize.py            Sanitización de contenido no confiable + redacción de secretos
└── session.py             Aislamiento de sesión por usuario (SessionContext)

servers/<dept>/             (dept = rrhh | finanzas | it | direccion)
├── database.py             Inicializa y siembra el SQLite del departamento
├── server.py                Servidor MCP — VERSIÓN VULNERABLE (Streamable HTTP)
├── server_hardened.py       Servidor MCP — VERSIÓN ENDURECIDA (Streamable HTTP)
├── Dockerfile / Dockerfile.hardened
└── (rrhh: descriptions.json · it: configs/, secrets/ · finanzas: vendor/, dependencies.lock.json)

servers/shadow-analytics/   Servidor MCP NO gobernado (fuera de servers/registry.json y de Docker)
servers/registry.json       Inventario de servidores MCP aprobados

exfil-listener/              "Servidor del atacante": recibe y registra datos exfiltrados (con panel web)
tools/
├── mcp_scan_lite.py          Analizador estático simplificado de descripciones de tools
├── generate_lockfile.py      Genera dependencies.lock.json (hashes de dependencias vendorizadas)
├── verify_dependencies.py    Verifica integridad de dependencias vendorizadas (gate CI/CD)
├── check_shadow_servers.py   Detecta servidores MCP no registrados
└── issue_token.py            CLI de login: emite un session_token de prueba para un usuario

mcp-config/                  Configuración lista para importar en Claude Desktop / VS Code (URLs HTTP)
scenarios/<01..10>_*/         Un README.md por cada categoría OWASP MCP Top 10 (sin scripts:
                              se reproducen a mano, hablando con el asistente conectado a los
                              servidores MCP reales)
logs/audit.log                Generado en tiempo de ejecución por las versiones endurecidas
siem/                         SIEM opcional (Wazuh + Grafana) sobre logs/audit.log — ver siem/README.md
docker-compose.vulnerable.yml Despliega los 4 servidores vulnerables + su propio exfil-listener
docker-compose.hardened.yml   Despliega los 4 servidores endurecidos + su exfil-listener + SIEM (Wazuh/Grafana)
```

## Departamentos y tools expuestas

| Servidor | Puerto vulnerable | Puerto endurecida | Tools | Resource |
|---|---|---|---|---|
| **RRHH** (`hr.*`) | 9001 | 9011 | `get_employee`, `list_employees` | `hr://organigrama` |
| **Finanzas** (`fin.*`) | 9002 | 9012 | `query_invoices`, `get_salary_report`, `get_cached_report` | — |
| **IT** (`it.*`) | 9003 | 9013 | `read_config`, `send_notification`, `create_ticket` | `it://tickets/latest` |
| **Dirección** (`dir.*`) | 9004 | 9014 | `get_strategic_documents` | — |
| **shadow-analytics** (no oficial, no Docker) | 9099 (única versión) | — | `run_query` | — |

### Roles y usuarios de prueba (`common/auth.py`)

| Usuario | Rol | Departamento |
|---|---|---|
| `ana.garcia` | `employee` | RRHH |
| `luis.perez` | `dept_manager` | RRHH |
| `marta.ruiz` | `employee` | Finanzas |
| `carlos.soto` | `dept_manager` | Finanzas |
| `elena.vidal` | `it_admin` | IT |
| `javier.leon` | `employee` | IT |
| `sofia.reyes` | `director` | Dirección |

## Puesta en marcha

### 1. Desplegar con Docker Compose

Cada fichero es una organización completa e independiente (uno para la versión vulnerable y otro para la versión endurecida).

```bash
docker compose -f docker-compose.vulnerable.yml up -d --build
docker compose -f docker-compose.hardened.yml up -d --build
```

Cada uno levanta sus 4 servidores (uno por departamento) y un `exfil-listener` propio en el puerto 8888. Es recomendable solo desplegar uno de los dos ya que si se levantan los dos ficheros a la vez, sus dos `exfil-listener` chocan en ese puerto (solo puede haber uno escuchando en 8888).

`docker-compose.hardened.yml` incluye también el SIEM (Wazuh + Grafana, ver punto 7). **Antes de su primer `up`**, genera los certificados que esos servicios necesitan (si no, `wazuh.indexer` falla al arrancar con un error de montaje):

```bash
docker compose -f siem/wazuh/generate-certs.docker-compose.yml run --rm generator
```

### 2. Conectar tu cliente MCP (Claude Desktop, VS Code, Cursor, Claude Code...)

Con el laboratorio ya arrancado, ver [`mcp-config/README.md`](mcp-config/README.md): un fichero de configuración por cliente, con nombre descriptivo, todos apuntando por URL a los mismos puertos de `docker-compose.vulnerable.yml` / `docker-compose.hardened.yml`.

Para inspeccionar un servidor suelto sin cliente de chat:

```bash
npx @modelcontextprotocol/inspector
# y conectar manualmente a http://localhost:9002/mcp, por ejemplo
```

### 3. El exfil-listener

Ya queda arrancado junto con el fichero de compose que uses, en `http://localhost:8888`. Abrir esa URL en el navegador muestra un **panel web** con lo capturado (timestamp, IP de origen, payload formateado y una etiqueta `BACKDOOR`/`EXFILTRADO` según el caso), que se auto-actualiza cada 2s. El botón "Vaciar log" limpia el historial entre pruebas. Ver [`exfil-listener/README.md`](exfil-listener/README.md).

### 4. shadow-analytics (fuera de Docker, a propósito)

```bash
python -m venv .venv && .venv\Scripts\activate   # o source .venv/bin/activate
pip install -r requirements.txt
python servers/shadow-analytics/server.py
```

Escucha en `http://127.0.0.1:9099/mcp`. No tiene Dockerfile ni entrada en ningún `docker-compose.*.yml`: representa un servidor MCP desplegado fuera de la infraestructura gobernada (ver escenario 09).

### 5. Reproducir un escenario de ataque

Los escenarios **no son scripts**: se reproducen conversando con un cliente MCP real (Claude Desktop, VS Code, o directamente MCP Inspector) conectado a los servidores correspondientes, tal y como haría un usuario o un atacante en el mundo real.

1. Asegúrate de que el fichero de compose que corresponda (`docker-compose.vulnerable.yml` y/o `docker-compose.hardened.yml`) está arriba y de que el/los servidor(es) que indique el escenario están conectados en tu cliente (ver [`mcp-config/`](mcp-config/README.md)).
2. Si el escenario lo requiere, obtén un `session_token` para probar la versión endurecida:
   ```bash
   python tools/issue_token.py <usuario>   # p. ej. sofia.reyes, luis.perez...
   ```
3. Abre `scenarios/NN_*/README.md` y sigue sus apartados: **Objetivo**, **Servidor(es) MCP involucrados**, **Tool(s) MCP invocada(s)**, **Query a realizar al LLM** e **Información que se espera extraer**. Pégale al asistente la query indicada (y el `session_token`, si aplica) tal cual.

Cuando un escenario necesita una preparación manual (envenenar una descripción, tamperear un fichero, crear un ticket malicioso), el propio README del escenario explica cómo proceder. 

### 6. Herramientas de análisis pre-despliegue

```bash
python tools/mcp_scan_lite.py "servers/*/descriptions.json"        # Tool Poisoning (MCP03)
python tools/verify_dependencies.py servers/finanzas/dependencies.lock.json  # Supply Chain (MCP04)
python tools/check_shadow_servers.py                                # Shadow MCP Servers (MCP09)
```

Ver [`tools/README.md`](tools/README.md) para qué hace cada una (incluida `issue_token.py`, la CLI de login usada en los escenarios contra la versión endurecida). Estas utilidades se ejecutan en el host, no dentro de Docker.

### 7. SIEM (Wazuh + Grafana) incluido en el despliegue endurecido

Añade trazabilidad real de accesos indebidos (mitigación de MCP08) sobre `logs/audit.log`: Wazuh genera una alerta por cada llamada denegada por RBAC y Grafana la visualiza en un panel. Los 4 servicios (`wazuh.manager`, `wazuh.indexer`, `wazuh.dashboard`, `grafana`) están definidos en el mismo `docker-compose.hardened.yml`, no en un fichero aparte — suben y bajan junto con los servidores MCP. Si no lo quieres, basta con borrar esos 4 servicios (y las entradas de `volumes:`/`networks:` que usan) del fichero. Ver [`siem/README.md`](siem/README.md) para el detalle completo: arquitectura, credenciales, cómo comprobarlo y por qué el `ossec.conf` está deliberadamente recortado para no disparar el tiempo de despliegue.

## Los 10 escenarios (uno por categoría OWASP MCP Top 10)

| # | Carpeta | Categoría OWASP MCP Top 10 |
|---|---|---|
| 01 | `01_token_mismanagement_secret_exposure` | MCP01:2025 — Token Mismanagement & Secret Exposure |
| 02 | `02_privilege_escalation_scope_creep` | MCP02:2025 — Privilege Escalation via Scope Creep |
| 03 | `03_tool_poisoning` | MCP03:2025 — Tool Poisoning (Description Injection + Rug Pull) |
| 04 | `04_supply_chain_dependency_tampering` | MCP04:2025 — Software Supply Chain Attacks & Dependency Tampering |
| 05 | `05_command_injection_execution` | MCP05:2025 — Command Injection & Execution (SQLi + Path Traversal + encoding bypass) |
| 06 | `06_intent_flow_subversion` | MCP06:2025 — Intent Flow Subversion |
| 07 | `07_insufficient_auth_authorization` | MCP07:2025 — Insufficient Authentication & Authorization |
| 08 | `08_lack_of_audit_telemetry` | MCP08:2025 — Lack of Audit and Telemetry |
| 09 | `09_shadow_mcp_servers` | MCP09:2025 — Shadow MCP Servers |
| 10 | `10_context_injection_oversharing` | MCP10:2025 — Context Injection & Over-Sharing |



