# siem/ — Trazabilidad de accesos indebidos

Añade observabilidad real sobre el `audit.log` que ya generan los 4 servidores **hardened** (`common/logging_utils py::log_tool_call`): un SIEM (Wazuh) que genera alertas cuando el RBAC deniega un acceso, y un panel (Grafana) para visualizarlas. Mitigación de **OWASP MCP08:2025 (Lack of Audit and Telemetry)**.

Se levanta desde el **mismo** `docker-compose.hardened.yml` (no hay un fichero compose separado): los servicios `wazuh.manager`, `wazuh.indexer`, `wazuh.dashboard` y `grafana` forman parte del despliegue endurecido junto a los 4 servidores MCP, y suben y bajan con él. No modifica ningún servidor MCP: lee `logs/audit.log`, la misma carpeta que ya montan los 4 servidores.

## Arquitectura

```
rrhh/finanzas/it/direccion (hardened) --> carpeta ./logs (bind mount) --> wazuh.manager (localfile JSON)
                                                                          |
                                                                    regla local 100101
                                                                    (success:false = acceso denegado)
                                                                          |
                                                                    wazuh.indexer (OpenSearch)
                                                                      /              \
                                                          wazuh.dashboard          grafana
                                                          (alertas nativas)   (panel "Accesos indebidos")
```

Wazuh **no** habla con los servidores MCP ni con exfil-listener: solo lee `logs/audit.log` en el host, la misma carpeta que ya montan los 4 servicios en `/app/logs` (ver [scenarios/08_lack_of_audit_telemetry](../scenarios/08_lack_of_audit_telemetry/README.md)). No hace falta agente Wazuh en cada servidor: el manager monta esa misma carpeta y la lee directamente como `<localfile>` en formato `json`.

## Alertas

`siem/wazuh/config/wazuh_cluster/local_rules.xml` define dos reglas:

- **`100100`** (nivel 3): dispara con cualquier línea de `audit.log` — solo sirve de regla padre.
- **`100101`** (nivel 10, grupo `access_denied`): dispara cuando, además, el campo `success` es `false`, es decir, toda vez que `require_role()` (`common/auth.py`) deniega una llamada por falta de permisos.

El panel de Grafana filtra únicamente por `rule.id:100101` — solo enseña accesos denegados, nunca tráfico normal:

| Panel | Qué muestra |
|---|---|
| Accesos denegados (24h) | Contador total |
| Accesos denegados por servidor MCP | Barras por `data.tool` (qué tool recibe más denegaciones) |
| Accesos denegados en el tiempo | Serie temporal |
| Últimos accesos denegados | Tabla con el detalle crudo de cada evento |

Se refresca cada 30s, ventana de las últimas 24h por defecto.

## Puesta en marcha

### 1. Generar los certificados (paso único)

Wazuh exige TLS entre manager, indexer y dashboard. Antes del primer
arranque:

```bash
docker compose -f siem/wazuh/generate-certs.docker-compose.yml run --rm generator
```

Esto crea `siem/wazuh/certs/wazuh-indexer-certs/` con los `.pem` que ya referencia `docker-compose.hardened.yml`. Es un paso único: no hace falta repetirlo salvo que se borre esa carpeta.

### 2. Arrancar (todo el laboratorio endurecido, un único fichero)

```bash
docker compose -f docker-compose.hardened.yml up -d --build
```

Deja disponibles, además de los 4 servidores MCP endurecidos y su `exfil-listener`:

| Servicio | URL | Credenciales |
|---|---|---|
| Wazuh dashboard | https://localhost:5602 | `admin` / `SecretPassword` |
| Wazuh indexer (API REST) | https://localhost:9200 | `admin` / `SecretPassword` |
| Grafana | http://localhost:3001 | `hispalis-admin` / `ChangeMe123!` |

Todas son credenciales de laboratorio; deben cambiarse si estos puertos se exponen más allá de `localhost`.

### 3. Generar accesos denegados de prueba

Cualquier escenario que provoque un `PermissionError` en un servidor hardened (por ejemplo, [scenarios/07_insufficient_auth_authorization/](../scenarios/07_insufficient_auth_authorization/README.md) sin token, o un `employee` pidiendo la ficha de otro compañero) escribe una línea con `"success": false` en `audit.log`. En segundos debería aparecer como fila nueva en el panel de Grafana — la comprobación práctica de [scenarios/08_lack_of_audit_telemetry/](../scenarios/08_lack_of_audit_telemetry/README.md) (MCP08).

### 4. Detener el despliegue

```bash
docker compose -f docker-compose.hardened.yml down -v
```

Para detener solo el SIEM y mantener los servidores MCP arriba, basta con eliminar los 4 servicios de Wazuh/Grafana de `docker-compose.hardened.yml` (y las entradas correspondientes de `volumes:`/`networks:`): los 4 servidores MCP y el `exfil-listener` no dependen de ellos para nada.

## Estructura

```
siem/
├── wazuh/
│   ├── generate-certs.docker-compose.yml   # generación de certificados (paso 1)
│   ├── certs/                              # certificados generados (no versionado)
│   └── config/                             # ossec.conf, reglas, config de indexer y dashboard
└── grafana/
    └── provisioning/                       # datasource y dashboard de Grafana
```
