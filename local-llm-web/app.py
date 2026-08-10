"""Version web de tools/local_llm_chat.py: mismo chat, con interfaz HTTP en vez de terminal (ver mcp-config/README.md)."""
from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import AnyUrl, BaseModel

from mcp import ClientSession, types
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.context import RequestContext

OLLAMA_CHAT_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")
MAX_TOOL_ROUNDS = 5
CONNECT_RETRIES = 10
CONNECT_RETRY_DELAY_SECONDS = 3.0
SYSTEM_PROMPT = (
    "Eres el asistente interno de Hispalis Technologies. Tienes acceso a las "
    "herramientas MCP conectadas para responder a las peticiones del usuario."
)
STATIC_DIR = Path(__file__).parent / "static"

CONFIG: dict = {"servers": [], "model": "llama3.1"}
STATE: dict = {"tool_owner": {}, "resource_owner": {}, "ollama_tools": [], "messages": []}

async def auto_accept_elicitation(
    context: RequestContext[ClientSession, None], params: types.ElicitRequestParams
) -> types.ElicitResult:
    """Acepta automaticamente cualquier confirmacion HITL (ver servers/it/server_hardened.py) -- no hay un usuario humano detras de este harness."""
    print(f"[elicitation] '{params.message}' -> auto-aceptada")
    defaults: dict[str, str | int | float | bool | list[str] | None] = {}
    for name, prop in (params.requestedSchema.get("properties") or {}).items():
        prop_type = prop.get("type")
        if prop_type == "boolean":
            defaults[name] = True
        elif prop_type == "string":
            defaults[name] = ""
        elif prop_type in ("integer", "number"):
            defaults[name] = 0
        elif prop_type == "array":
            defaults[name] = []
    return types.ElicitResult(action="accept", content=defaults)

def mcp_tool_to_ollama(tool) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.inputSchema,
        },
    }

def resource_tool_name(uri: str) -> str:
    return "read_resource_" + re.sub(r"[^a-zA-Z0-9_]", "_", uri.replace("://", "_"))

def mcp_resource_to_ollama(resource) -> dict:
    return {
        "type": "function",
        "function": {
            "name": resource_tool_name(str(resource.uri)),
            "description": f"[Resource MCP {resource.uri}] {resource.description or ''}",
            "parameters": {"type": "object", "properties": {}},
        },
    }

async def connect_with_retry(url: str, stack: AsyncExitStack) -> ClientSession:
    """Reintenta la conexion -- en Docker los demas servidores pueden tardar unos segundos en estar listos."""
    for attempt in range(1, CONNECT_RETRIES + 1):
        try:
            read_stream, write_stream, _ = await stack.enter_async_context(streamable_http_client(url))
            session = await stack.enter_async_context(
                ClientSession(read_stream, write_stream, elicitation_callback=auto_accept_elicitation)
            )
            await session.initialize()
            return session
        except Exception as exc:
            print(f"No se pudo conectar a {url} (intento {attempt}/{CONNECT_RETRIES}): {exc}")
            if attempt == CONNECT_RETRIES:
                raise
            await asyncio.sleep(CONNECT_RETRY_DELAY_SECONDS)
    raise RuntimeError(f"No se pudo conectar a {url}")

@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with AsyncExitStack() as stack:
        tool_owner: dict[str, ClientSession] = {}
        resource_owner: dict[str, tuple[ClientSession, str]] = {}
        ollama_tools: list[dict] = []

        for url in CONFIG["servers"]:
            session = await connect_with_retry(url, stack)
            listed = await session.list_tools()
            listed_resources = await session.list_resources()

            for tool in listed.tools:
                tool_owner[tool.name] = session
                ollama_tools.append(mcp_tool_to_ollama(tool))

            for resource in listed_resources.resources:
                resource_owner[resource_tool_name(str(resource.uri))] = (session, str(resource.uri))
                ollama_tools.append(mcp_resource_to_ollama(resource))

            print(
                f"Conectado a {url} -- tools: {[t.name for t in listed.tools]} "
                f"-- resources: {[str(r.uri) for r in listed_resources.resources]}"
            )

        STATE["tool_owner"] = tool_owner
        STATE["resource_owner"] = resource_owner
        STATE["ollama_tools"] = ollama_tools
        STATE["messages"] = [{"role": "system", "content": SYSTEM_PROMPT}]
        yield

app = FastAPI(title="Hispalis Technologies -- Asistente interno", lifespan=lifespan)

class ChatRequest(BaseModel):
    message: str

async def call_ollama(messages: list[dict], tools: list[dict]) -> dict:
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            OLLAMA_CHAT_URL,
            json={"model": CONFIG["model"], "messages": messages, "tools": tools, "stream": False},
        )
        if response.status_code >= 400:
            return {
                "message": {
                    "role": "assistant",
                    "content": f"ERROR de Ollama ({response.status_code}): {response.text}",
                }
            }
        return response.json()

@app.post("/api/chat")
async def chat(req: ChatRequest) -> dict:
    messages = STATE["messages"]
    tool_owner: dict[str, ClientSession] = STATE["tool_owner"]
    resource_owner: dict[str, tuple[ClientSession, str]] = STATE["resource_owner"]
    ollama_tools = STATE["ollama_tools"]

    messages.append({"role": "user", "content": req.message})
    events: list[dict] = []

    for _ in range(MAX_TOOL_ROUNDS):
        data = await call_ollama(messages, ollama_tools)
        message = data["message"]
        messages.append(message)

        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            return {"reply": message.get("content", ""), "events": events}

        for call in tool_calls:
            name = call["function"]["name"]
            arguments = call["function"].get("arguments") or {}
            events.append({"type": "tool_call", "name": name, "arguments": arguments})

            if name in resource_owner:
                session, uri = resource_owner[name]
                try:
                    result = await session.read_resource(AnyUrl(uri))
                    result_text = "\n".join(
                        block.text for block in result.contents if hasattr(block, "text")
                    )
                except Exception as exc:
                    result_text = f"ERROR leyendo resource '{uri}': {exc}"
            else:
                session = tool_owner.get(name)
                if session is None:
                    result_text = f"ERROR: tool '{name}' no disponible en ningun servidor conectado."
                else:
                    result = await session.call_tool(name, arguments)
                    result_text = "\n".join(
                        block.text for block in result.content if hasattr(block, "text")
                    )
                    if result.isError:
                        result_text = f"ERROR: {result_text}"

            events.append({"type": "tool_result", "name": name, "result": result_text})
            messages.append({"role": "tool", "tool_name": name, "content": result_text})

    return {
        "reply": "(demasiadas llamadas a herramientas encadenadas, se corta aqui)",
        "events": events,
    }

@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC_DIR / "chat.html").read_text(encoding="utf-8")

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Chat web (aspecto de asistente interno de empresa) conectado a servidores MCP y a Ollama."
    )
    parser.add_argument(
        "--server",
        action="append",
        dest="servers",
        default=None,
        help=(
            "URL de un servidor MCP (repetible: --server URL1 --server URL2 ...). "
            "Si no se indica, se usa la variable de entorno MCP_SERVERS (URLs separadas por comas)."
        ),
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OLLAMA_MODEL", "llama3.1"),
        help="Modelo de Ollama a usar (por defecto: llama3.1, o la variable de entorno OLLAMA_MODEL)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "8000")),
        help="Puerto del chat web (por defecto: 8000, o la variable de entorno PORT)",
    )
    args = parser.parse_args()

    servers = args.servers or [
        url.strip() for url in os.environ.get("MCP_SERVERS", "").split(",") if url.strip()
    ]
    if not servers:
        parser.error("no se ha indicado ningun servidor MCP (usa --server o la variable de entorno MCP_SERVERS)")

    CONFIG["servers"] = servers
    CONFIG["model"] = args.model

    uvicorn.run(app, host="0.0.0.0", port=args.port)
    return 0

if __name__ == "__main__":
    sys.exit(main())
