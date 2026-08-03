"""Servidor MCP "Shadow Analytics" — NO FORMA PARTE de la organización oficial."""
from __future__ import annotations

import os
import sqlite3
from mcp.server.fastmcp import FastMCP

# Apunta directamente a la base de datos de Finanzas, sin pasar por su capa de tools.
FINANZAS_DB_PATH = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "..", "finanzas", "finanzas.db")
)

# Fuera de docker-compose.*.yml a propósito: se lanza a mano (ver servers/README.md).
MCP_HTTP_HOST = os.environ.get("MCP_HTTP_HOST", "127.0.0.1")
MCP_HTTP_PORT = int(os.environ.get("MCP_HTTP_PORT", "9099"))

mcp = FastMCP(
    "shadow-analytics (NO OFICIAL)",
    instructions=(
        "Servidor MCP de analitica ad-hoc, desplegado por conveniencia y NO registrado "
        "en servers/registry.json. Uso interno no autorizado."
    ),
    host=MCP_HTTP_HOST,
    port=MCP_HTTP_PORT,
    streamable_http_path="/mcp",
)

@mcp.tool(
    description="Ejecuta una consulta SQL arbitraria contra la base de datos de Finanzas."
)
def run_query(sql: str) -> str:
    # Sin RBAC, sin validacion, sin whitelist de sentencias, sin logging.
    conn = sqlite3.connect(FINANZAS_DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        if cursor.description is not None:
            columns = [d[0] for d in cursor.description]
            rows = cursor.fetchall()
            result = str([dict(zip(columns, row)) for row in rows])
        else:
            conn.commit()
            result = f"OK, {cursor.rowcount} fila(s) afectada(s)."
    except sqlite3.Error as exc:
        result = f"Error SQL: {exc}"
    finally:
        conn.close()
    return result

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
