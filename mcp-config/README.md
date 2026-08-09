# Configuración MCP para clientes/hosts

Un fichero de configuración por cliente MCP, todos en esta misma carpeta, con nombre descriptivo. Desde que el laboratorio se despliega con Docker Compose (transporte **Streamable HTTP**, ver [`docker-compose.vulnerable.yml`](../docker-compose.vulnerable.yml) y [`docker-compose.hardened.yml`](../docker-compose.hardened.yml)), conectar un
cliente no consiste en decirle qué comando lanzar, sino darle directamente la **URL** de cada servidor — que debe estar ya arrancado.

Todos registran los 4 servidores departamentales (versión **vulnerable** y **hardened** por separado, 8 entradas) más `hispalis-shadow-analytics-UNOFFICIAL` (el servidor no gobernado del escenario 09 — no está en ningún `docker-compose.*.yml`, hay que arrancarlo a mano, ver más abajo).

| Cliente | Fichero | Formato |
|---|---|---|
| Claude Desktop | [`claude-desktop-mcp-config.json`](claude-desktop-mcp-config.json) | `mcpServers`, cada entrada con `"command": "npx"` + `"args": ["-y", "mcp-remote", "<url>"]` |
| VS Code (Copilot Chat, modo agent) | [`vscode-mcp-config.json`](vscode-mcp-config.json) | `servers`, cada entrada con `"type": "http"` + `"url"` |
| Cursor | [`cursor-mcp-config.json`](cursor-mcp-config.json) | `mcpServers`, cada entrada con `"type": "http"` + `"url"` |


##  MCP Inspector

A diferencia de los otros tres, Inspector no lee ningún fichero de configuración: es una UI web en la que se pega la URL manualmente, servidor a servidor. Es también la forma más fiable de invocar una tool con un payload exacto sin depender de que un asistente lo transcriba bien. Pasos para ejecutarlo:

1. Se lanza con el comando:
   ```bash
   npx @modelcontextprotocol/inspector
   ```
2. Se abre en el navegador la URL que imprime la terminal (normalmente
   `http://localhost:6274`, con un token de sesión incluido en versiones recientes). Cabe destacar que es probable que la página se abra sola.
3. En el formulario de conexión:
   - **Transport Type:** debe cambiarse explícitamente a `Streamable HTTP`.
   - **URL:** la del servidor que se quiera probar. Por ejemplo:
     `http://localhost:9002/mcp` (Finanzas vulnerable) — con la `/mcp` incluida.
   - Cabeceras vacías: ninguno de nuestros servidores exige autenticación a nivel
     de transporte.
4. Al pulsar **Connect**, con el fichero de compose correspondiente arrancado, aparecen las pestañas **Tools / Resources / Prompts**.
5. En **Tools**, se elige la tool, se rellena el formulario de parámetros con el payload exacto del escenario y se pulsa **Run Tool**. Para probar la versión endurecida, se añade `session_token` como parámetro adicional, con el valor de `python tools/issue_token.py <usuario>`.

## Modelo local (Ollama)

Alternativa a los cuatro clientes anteriores para reproducir los escenarios contra un modelo que **no** tiene el alineamiento/entrenamiento de seguridad de Claude — útil cuando se quiere observar el efecto de una tool poisoning/prompt injection sin que el modelo la reconozca y la rechace por su cuenta. No añade ningún system prompt de seguridad ni detección de prompt injection propia: lo que el modelo haga con el contenido de una tool depende solo de él.

Requiere [Ollama](https://ollama.com/) instalado en el host, con un modelo que soporte tool-calling ya descargado:

```bash
ollama pull llama3.1
```

Hay dos formas de usarlo:

- **Chat web (`local-llm-chat`, recomendado):** se despliega solo, como un servicio más de `docker-compose.vulnerable.yml`/`docker-compose.hardened.yml` — sube y baja con el resto del laboratorio, conectado ya a los 4 servidores departamentales de ese fichero. Solo hace falta abrir `http://localhost:8000`. Ver [`local-llm-web/README.md`](../local-llm-web/README.md) para configurar el modelo u otros servidores.
- **CLI (`tools/local_llm_chat.py`):** para uso manual/puntual desde terminal, con control fino de qué servidores conectar en cada momento:
  ```bash
  python tools/local_llm_chat.py --server http://localhost:9001/mcp --server http://localhost:9004/mcp --model qwen2.5:7b
  ```

En ambos casos, se escribe la misma query que indica el escenario tal cual, y para la versión endurecida se incluye el `session_token` (`python tools/issue_token.py <usuario>`) en el propio mensaje, igual que con los demás clientes. Cada `tool_call` y su resultado se muestran como evidencia (en el chat web, como nota técnica entre mensajes; en la CLI, por consola).

Los resources MCP (como `it://tickets/latest`, usado en el escenario 06) también están disponibles: se exponen al modelo como tools sintéticas de solo lectura, ya que Ollama no tiene un concepto nativo de "resource".

