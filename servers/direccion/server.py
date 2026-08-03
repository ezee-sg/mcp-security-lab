"""Servidor MCP de Dirección — VERSIÓN VULNERABLE (ver servers/README.md)."""
from __future__ import annotations
import os
import sqlite3
from mcp.server.fastmcp import FastMCP
from database import DB_PATH, init_db

init_db()

MCP_HTTP_HOST = os.environ.get("MCP_HTTP_HOST", "127.0.0.1")
MCP_HTTP_PORT = int(os.environ.get("MCP_HTTP_PORT", "9004"))

mcp = FastMCP(
    "Hispalis Dirección (vulnerable)",
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
def get_strategic_documents(classification: str) -> str:
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
    return str(rows)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
