# local-llm-web/

Versión web de [`tools/local_llm_chat.py`](../tools/local_llm_chat.py): misma lógica de conexión a servidores MCP y a un modelo local (Ollama), pero con aspecto de chat interno de empresa en vez de terminal. Se despliega como un servicio más (`local-llm-chat`) tanto en `docker-compose.vulnerable.yml` como en `docker-compose.hardened.yml` — sube y baja junto con el resto del laboratorio, sin ningún paso manual.

No añade ningún system prompt de seguridad ni detección de prompt injection propia: lo que el modelo decida hacer con el contenido de una tool depende únicamente de su propio alineamiento.

## Requisito: Ollama en el host

El contenedor no trae ningún modelo — llama al Ollama que corre en la máquina anfitriona (`http://host.docker.internal:11434`), igual que si se usara [`tools/local_llm_chat.py`](../tools/local_llm_chat.py) en local. Antes de levantar el compose:

```bash
ollama pull llama3.1
```

(y tener Ollama arrancado — se inicia solo tras instalarlo, o con `ollama serve`).

## Puesta en marcha

```bash
docker compose -f docker-compose.vulnerable.yml up -d --build
```

o

```bash
docker compose -f docker-compose.hardened.yml up -d --build
```

Y abrir `http://localhost:8000`. El contenedor se conecta automáticamente a los 4 servidores departamentales de ese mismo fichero de compose (los 4 a la vez, para no tener que reconfigurar nada entre escenarios) y reintenta la conexión varias veces por si esos servidores tardan unos segundos en arrancar.

| Variable de entorno | Para qué sirve | Valor por defecto en el compose |
|---|---|---|
| `MCP_SERVERS` | URLs de los servidores MCP, separadas por comas | los 4 del fichero de compose correspondiente |
| `OLLAMA_URL` | Endpoint de chat de Ollama | `http://host.docker.internal:11434/api/chat` |
| `OLLAMA_MODEL` | Modelo de Ollama a usar | `llama3.1` |

Para cambiar de modelo sin editar el compose: `OLLAMA_MODEL=qwen2.5:7b docker compose -f docker-compose.vulnerable.yml up -d --build local-llm-chat` (o directamente editar la línea `OLLAMA_MODEL` del servicio).

## Uso manual (sin Docker)

`app.py` también acepta flags de línea de comandos en vez de variables de entorno, para ejecución nativa fuera del compose:

```bash
python local-llm-web/app.py --server http://localhost:9001/mcp --server http://localhost:9004/mcp --model qwen2.5:7b
```

## Estructura

```
local-llm-web/
├── Dockerfile
├── app.py               FastAPI: conecta los servidores MCP y llama a Ollama
└── static/chat.html      Interfaz de chat (HTML/CSS/JS, sin dependencias externas)
```

Cada `tool_call`/`tool_result` se muestra en el chat como una nota técnica entre los mensajes, igual que en la versión de terminal — útil como evidencia.
