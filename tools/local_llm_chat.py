"""Chat interactivo con un modelo local (Ollama) conectado a servidores MCP (ver mcp-config/README.md)."""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
from contextlib import AsyncExitStack

import httpx
from pydantic import AnyUrl
from mcp import ClientSession, types
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.context import RequestContext

OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
MAX_TOOL_ROUNDS = 5

async def auto_accept_elicitation(
    context: RequestContext[ClientSession, None], params: types.ElicitRequestParams
) -> types.ElicitResult:
    """Acepta automaticamente cualquier confirmacion HITL (ver servers/it/server_hardened.py) -- no hay un usuario humano detras de este harness."""
    print(f"  [elicitation] '{params.message}' -> auto-aceptada")
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
SYSTEM_PROMPT = (
    "Eres el asistente interno de Hispalis Technologies. Tienes acceso a las "
    "herramientas MCP conectadas para responder a las peticiones del usuario."
)

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

async def connect_servers(
    urls: list[str], stack: AsyncExitStack
) -> tuple[dict[str, ClientSession], dict[str, tuple[ClientSession, str]], list[dict]]:
    """Conecta a cada URL y devuelve (tool_name -> session, resource_tool_name -> (session, uri), tools en formato Ollama)."""
    tool_owner: dict[str, ClientSession] = {}
    resource_owner: dict[str, tuple[ClientSession, str]] = {}
    ollama_tools: list[dict] = []

    for url in urls:
        read_stream, write_stream, _ = await stack.enter_async_context(streamable_http_client(url))
        session = await stack.enter_async_context(
            ClientSession(read_stream, write_stream, elicitation_callback=auto_accept_elicitation)
        )
        await session.initialize()
        listed = await session.list_tools()
        listed_resources = await session.list_resources()

        for tool in listed.tools:
            if tool.name in tool_owner:
                print(f"AVISO: tool '{tool.name}' duplicada entre servidores, se usa la de {url}.")
            tool_owner[tool.name] = session
            ollama_tools.append(mcp_tool_to_ollama(tool))

        for resource in listed_resources.resources:
            resource_owner[resource_tool_name(str(resource.uri))] = (session, str(resource.uri))
            ollama_tools.append(mcp_resource_to_ollama(resource))

        print(
            f"Conectado a {url} -- tools: {[t.name for t in listed.tools]} "
            f"-- resources: {[str(r.uri) for r in listed_resources.resources]}"
        )

    return tool_owner, resource_owner, ollama_tools

async def call_ollama(model: str, messages: list[dict], tools: list[dict]) -> dict:
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            OLLAMA_CHAT_URL,
            json={"model": model, "messages": messages, "tools": tools, "stream": False},
        )
        if response.status_code >= 400:
            print(f"\nERROR de Ollama ({response.status_code}): {response.text}")
            print("(¿el modelo indicado tiene soporte de 'tools' en Ollama? ver https://ollama.com/library)\n")
            response.raise_for_status()
        return response.json()

def print_tools(ollama_tools: list[dict]) -> None:
    for entry in ollama_tools:
        fn = entry["function"]
        print(f"\n- {fn['name']}:\n  {fn['description']!r}")
    print()

async def run_chat(
    model: str,
    tool_owner: dict[str, ClientSession],
    resource_owner: dict[str, tuple[ClientSession, str]],
    ollama_tools: list[dict],
) -> None:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print("\nEscribe tu peticion ('/tools' para ver las descripciones tal cual las recibe el modelo, 'salir' para terminar).\n")

    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input or user_input.lower() in {"salir", "exit", "quit"}:
            break
        if user_input == "/tools":
            print_tools(ollama_tools)
            continue

        messages.append({"role": "user", "content": user_input})

        for _ in range(MAX_TOOL_ROUNDS):
            data = await call_ollama(model, messages, ollama_tools)
            message = data["message"]
            messages.append(message)

            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                print(f"\n{message.get('content', '')}\n")
                break

            for call in tool_calls:
                name = call["function"]["name"]
                arguments = call["function"].get("arguments") or {}
                print(f"  [tool_call] {name}({arguments})")

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

                print(f"  [tool_result] {result_text[:300]}")
                messages.append({"role": "tool", "tool_name": name, "content": result_text})
        else:
            print("\n(demasiadas llamadas a herramientas encadenadas, se corta aqui)\n")

async def main_async(args: argparse.Namespace) -> int:
    async with AsyncExitStack() as stack:
        tool_owner, resource_owner, ollama_tools = await connect_servers(args.server, stack)
        if not ollama_tools:
            print("Ningun servidor conectado expuso tools ni resources.")
            return 1
        await run_chat(args.model, tool_owner, resource_owner, ollama_tools)
    return 0

def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Chat con un modelo local (Ollama) conectado a servidores MCP, "
            "sin ningun system prompt de seguridad añadido por este harness."
        )
    )
    parser.add_argument(
        "--server",
        action="append",
        required=True,
        help="URL de un servidor MCP (repetible: --server URL1 --server URL2 ...)",
    )
    parser.add_argument("--model", default="llama3.1", help="Modelo de Ollama a usar (por defecto: llama3.1)")
    args = parser.parse_args()
    return asyncio.run(main_async(args))

if __name__ == "__main__":
    sys.exit(main())
