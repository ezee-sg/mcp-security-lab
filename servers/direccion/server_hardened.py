"""Servidor MCP de Dirección — VERSIÓN hardened (ver servers/README.md)."""
from __future__ import annotations
import os
import sqlite3
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from mcp.server.fastmcp import FastMCP
from common.auth import require_role
from common.logging_utils import log_tool_call
from database import DB_PATH, init_db

init_db()

MCP_HTTP_HOST = os.environ.get("MCP_HTTP_HOST", "127.0.0.1")
MCP_HTTP_PORT = int(os.environ.get("MCP_HTTP_PORT", "9014"))

mcp = FastMCP(
    "Hispalis Dirección (hardened)",
    instructions="Servidor MCP del departamento de Dirección de Hispalis Technologies.",
    host=MCP_HTTP_HOST,
    port=MCP_HTTP_PORT,
    streamable_http_path="/mcp",
)

@mcp.tool(
    description=(
        "Obtiene documentos estrategicos de la compania filtrados por clasificacion "
        "('internal', 'confidential' o 'all')."
    )
)
def get_strategic_documents(classification: str, session_token: str) -> str:
    try:
        payload = require_role(session_token, "director")
    except PermissionError as exc:
        log_tool_call(
            "dir.get_strategic_documents", {"classification": classification}, "unknown", str(exc), False
        )
        raise

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if classification == "all":
        cursor.execute("SELECT id, title, content, classification FROM strategic_documents")
    else:
        cursor.execute(
            "SELECT id, title, content, classification FROM strategic_documents WHERE classification = ?",
            (classification,),
        )
    rows = cursor.fetchall()
    conn.close()

    result = str(rows)
    log_tool_call(
        "dir.get_strategic_documents", {"classification": classification}, payload["role"], result, True
    )
    return result

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
