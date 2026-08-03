# Configuración MCP para clientes/hosts

Un fichero de configuración por cliente MCP, todos en esta misma carpeta, con
nombre descriptivo. Desde que el laboratorio se despliega con Docker Compose
(transporte **Streamable HTTP**, ver
[`docker-compose.vulnerable.yml`](../docker-compose.vulnerable.yml) y
[`docker-compose.hardened.yml`](../docker-compose.hardened.yml)), conectar un
cliente no consiste en decirle qué comando lanzar, sino darle directamente la
**URL** de cada servidor — que debe estar ya arrancado.

Todos registran los 4 servidores departamentales (versión **vulnerable** y
**hardened** por separado, 8 entradas) más `hispalis-shadow-analytics-UNOFFICIAL`
(el servidor no gobernado del escenario 09 — no está en ningún
`docker-compose.*.yml`, hay que arrancarlo a mano, ver más abajo).

| Cliente | Fichero | Formato |
|---|---|---|
| Claude Desktop | [`claude-desktop-mcp-config.json`](claude-desktop-mcp-config.json) | `mcpServers`, cada entrada con `"url"` |
| VS Code (Copilot Chat, modo agent) | [`vscode-mcp-config.json`](vscode-mcp-config.json) | `servers`, cada entrada con `"type": "http"` + `"url"` |
| Cursor | [`cursor-mcp-config.json`](cursor-mcp-config.json) | `mcpServers`, cada entrada con `"url"` (mismo formato que Claude Desktop) |
| Claude Code (CLI) | [`claude-code-mcp-config.json`](claude-code-mcp-config.json) | `mcpServers`, cada entrada con `"type": "http"` + `"url"` |


##  MCP Inspector

A diferencia de los otros cuatro, Inspector no lee ningún fichero de configuración:
es una UI web en la que pegas la URL manualmente, servidor a servidor. Es también
la forma más fiable de invocar una tool con un payload exacto sin depender de que
un asistente lo transcriba bien. Pasos para ejecutarlo:

1. Se lanza con el comando:
   ```bash
   npx @modelcontextprotocol/inspector
   ```
2. Abre en el navegador la URL que imprime la terminal (normalmente
   `http://localhost:6274`, con un token de sesión incluido en versiones recientes). Cabe destacar que es probable que la página se abra sola.
3. En el formulario de conexión:
   - **Transport Type:** cámbialo explícitamente a `Streamable HTTP`.
   - **URL:** la del servidor que se quiera probar. Por ejemplo:
     `http://localhost:9002/mcp` (Finanzas vulnerable) — con la `/mcp` incluida.
   - Cabeceras vacías: ninguno de nuestros servidores exige autenticación a nivel
     de transporte.
4. Pulsa **Connect**. Con el fichero de compose correspondiente arrancado verás las pestañas **Tools / Resources / Prompts**.
5. En **Tools**, elige la tool, rellena el formulario de parámetros con el payload exacto del escenario y pulsa **Run Tool**. Para probar la versión endurecida, añade `session_token` como parámetro más, con el valor de `python tools/issue_token.py <usuario>`.

