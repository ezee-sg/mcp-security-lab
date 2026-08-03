# siem/ — Trazabilidad de accesos indebidos (opcional)

Añade observabilidad real sobre el `audit.log` que ya generan los 4 servidores
**hardened** (`common/logging_utils.py::log_tool_call`), en vez de dejarlo como
un simple fichero JSON local: un SIEM (Wazuh) que genera alertas cuando el RBAC
deniega un acceso, y un panel (Grafana) para visualizarlas. Mitigación de
**OWASP MCP08:2025 (Lack of Audit and Telemetry)**.

Se levanta desde el **mismo** `docker-compose.hardened.yml` (no hay un fichero
compose separado): los servicios `wazuh.manager`, `wazuh.indexer`,
`wazuh.dashboard` y `grafana` viven ahí junto a los 4 servidores MCP. Es
opcional en el sentido de que no modifica ningún servidor MCP y se puede
borrar de ese fichero sin más si resulta demasiado pesado para el TFM — solo
lee `./logs`, la misma carpeta que ya montan los 4 servidores.

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

Wazuh **no** habla con los servidores MCP ni con exfil-listener: solo lee
`logs/audit.log` en el host, la misma carpeta que ya montan los 4 servicios de
`docker-compose.hardened.yml` en `/app/logs` (y que usan también en ejecución
nativa, ver [scenarios/08_lack_of_audit_telemetry](../scenarios/08_lack_of_audit_telemetry/README.md)).
No hace falta instalar un agente Wazuh en cada servidor: el manager monta esa
misma carpeta y la lee directamente como `<localfile>` en formato `json`.

La regla `100101` (`siem/wazuh/config/wazuh_cluster/local_rules.xml`) se
dispara sobre cualquier entrada de `audit.log` con `"success": false`, es
decir, toda vez que `require_role()` (`common/auth.py`) deniega una llamada a
una tool por falta de permisos — el "acceso indebido a información
restringida" que pedías trazar.

## Por qué pesa lo que pesa

Wazuh manager + indexer (OpenSearch) + dashboard son 3 imágenes reales de
varios cientos de MB cada una (la primera vez que se construya/descargue
puede tardar varios minutos, sobre todo el indexer). Para no añadir peso
innecesario:

- El `ossec.conf` (`wazuh_manager.conf`) que se usa aquí está **recortado a
  propósito**: sin FIM (`syscheck`), sin `vulnerability-detector`, sin SCA, sin
  rootcheck ni wodles de terceros. Su único trabajo es leer `audit.log` y
  aplicar las reglas locales — nada de lo que monitoriza un Wazuh de
  producción real (ficheros del sistema, CVEs, cumplimiento) tiene sentido
  aquí, porque no hay ningún host que auditar más allá del propio audit log.
- No se despliega ningún agente Wazuh (`wazuh-agent`): no hace falta, el
  manager lee el fichero directamente.
- Grafana usa el datasource **Elasticsearch** que ya trae Grafana OSS por
  defecto (compatible con el API REST de OpenSearch para las agregaciones
  simples que necesita el dashboard), en vez del plugin
  `grafana-opensearch-datasource`: evita una descarga adicional del catálogo
  de plugins en cada arranque.

Si aun así resulta demasiado pesado para el TFM, basta con borrar los 4
servicios (`wazuh.manager`, `wazuh.indexer`, `wazuh.dashboard`, `grafana`) de
`docker-compose.hardened.yml`: el resto del laboratorio (incluida la
auditoría en fichero) sigue funcionando exactamente igual sin ellos.

## Puesta en marcha

### 1. Generar los certificados (paso único)

Wazuh exige TLS entre manager, indexer y dashboard. Antes del primer
arranque, genera los certificados con la propia herramienta oficial de Wazuh
(no se puede hacer sin ejecutar nada — es el único paso de este añadido que
requiere lanzar un contenedor antes de tiempo):

```bash
docker compose -f siem/wazuh/generate-certs.docker-compose.yml run --rm generator
```

Esto crea `siem/wazuh/certs/wazuh-indexer-certs/` con los `.pem` que ya
referencia `docker-compose.hardened.yml`. Es un paso único: no hace falta
repetirlo salvo que borres esa carpeta.

### 2. Arrancar (todo el laboratorio endurecido, un único fichero)

```bash
docker compose -f docker-compose.hardened.yml up -d --build
```

Deja disponibles, además de los 4 servidores MCP endurecidos y su
`exfil-listener`:

| Servicio | URL | Credenciales |
|---|---|---|
| Wazuh dashboard | https://localhost:5602 | `admin` / `SecretPassword` |
| Wazuh indexer (API REST) | https://localhost:9200 | `admin` / `SecretPassword` |
| Grafana | http://localhost:3001 | `hispalis-admin` / `ChangeMe123!` |

Todas son credenciales de laboratorio, iguales a las de ejemplo de la propia
documentación de Wazuh — cámbialas si expones estos puertos más allá de
`localhost`.

**Nota sobre `admin`/`SecretPassword`:** el hash bcrypt en
`siem/wazuh/config/wazuh_indexer/internal_users.yml` es el que usan los
tutoriales oficiales de Wazuh 4.x para esa contraseña. Si el login del
indexer/dashboard fallara, regenera el hash tú mismo (dentro del propio
contenedor, una vez arrancado) y sustitúyelo en ese fichero:

```bash
docker compose -f docker-compose.hardened.yml exec wazuh.indexer \
  bash /usr/share/wazuh-indexer/plugins/opensearch-security/tools/hash.sh -p 'SecretPassword'
```

### 3. Generar accesos denegados de prueba

Cualquier escenario que provoque un `PermissionError` en un servidor hardened
(por ejemplo, [scenarios/07_insufficient_auth_authorization/](../scenarios/07_insufficient_auth_authorization/README.md)
sin token, o un `employee` pidiendo la ficha de otro compañero) escribe una
línea con `"success": false` en `audit.log`. En segundos debería aparecer
como alerta de nivel 10 en el dashboard de Wazuh (grupo `access_denied`) y
como fila nueva en el panel de Grafana — la comprobación práctica de
[scenarios/08_lack_of_audit_telemetry/](../scenarios/08_lack_of_audit_telemetry/README.md)
(MCP08).

### 4. Quitarlo

```bash
docker compose -f docker-compose.hardened.yml down -v
```

Para quitar solo el SIEM y mantener los servidores MCP arriba, borra los 4
servicios de Wazuh/Grafana de `docker-compose.hardened.yml` (y las entradas
correspondientes de `volumes:`/`networks:`) — los 4 servidores MCP y el
`exfil-listener` no dependen de ellos para nada.

## Estructura

```
siem/
├── README.md
├── wazuh/
│   ├── generate-certs.docker-compose.yml   # paso 1, un solo uso
│   ├── certs/
│   │   ├── config.yml                      # nodos para el generador de certificados
│   │   └── wazuh-indexer-certs/            # certificados generados (no versionado)
│   └── config/
│       ├── wazuh_cluster/
│       │   ├── wazuh_manager.conf          # ossec.conf recortado + localfile de audit.log
│       │   └── local_rules.xml             # regla 100100/100101 (acceso denegado)
│       ├── wazuh_indexer/
│       │   ├── wazuh.indexer.yml           # opensearch.yml
│       │   └── internal_users.yml          # usuarios de demo (admin/SecretPassword)
│       └── wazuh_dashboard/
│           ├── opensearch_dashboards.yml
│           └── wazuh.yml                   # conexion dashboard -> API de Wazuh
└── grafana/
    └── provisioning/
        ├── datasources/wazuh-indexer.yml   # datasource Elasticsearch -> indexer
        └── dashboards/
            ├── dashboards.yml
            └── hispalis-accesos-indebidos.json
```
