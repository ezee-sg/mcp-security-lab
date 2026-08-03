"""Servidor MCP de Finanzas — VERSIÓN VULNERABLE (ver servers/README.md)."""
from __future__ import annotations
import os
import sqlite3
from mcp.server.fastmcp import FastMCP
from database import DB_PATH, init_db
from vendor.report_formatter import format_salary_report

init_db()

MCP_HTTP_HOST = os.environ.get("MCP_HTTP_HOST", "127.0.0.1")
MCP_HTTP_PORT = int(os.environ.get("MCP_HTTP_PORT", "9002"))

mcp = FastMCP(
    "Hispalis Finanzas (vulnerable)",
    instructions="Servidor MCP del departamento de Finanzas de Hispalis Technologies.",
    host=MCP_HTTP_HOST,
    port=MCP_HTTP_PORT,
    streamable_http_path="/mcp",
)

@mcp.tool(
    description=(
        "Consulta facturas de la base de datos. Acepta un filtro por estado "
        "(paid, pending, overdue)."
    )
)
def query_invoices(filter: str) -> str:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # VULNERABLE: concatenación directa del parámetro en la consulta SQL.
    query = f"SELECT * FROM invoices WHERE status = '{filter}'"
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
    except sqlite3.Error as exc:
        conn.close()
        return f"Error de base de datos: {exc}"
    conn.close()
    return str(rows)

# VULNERABLE: caché global sin aislar por sesión (ver servers/README.md).
_LAST_REPORT_CACHE: dict[str, str] = {}

@mcp.tool(
    description="Genera un informe de nominas por departamento ('all' para todos los departamentos)."
)
def get_salary_report(department: str) -> str:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if department == "all":
        cursor.execute("SELECT name, salary, department FROM employees")
    else:
        cursor.execute(
            "SELECT name, salary, department FROM employees WHERE department = ?",
            (department,),
        )
    rows = cursor.fetchall()
    conn.close()
    result = format_salary_report(rows)
    _LAST_REPORT_CACHE[department] = result
    return result

@mcp.tool(
    description=(
        "Devuelve el ultimo informe de nomina generado para un departamento, "
        "sin necesidad de volver a consultarlo (optimizacion de rendimiento)."
    )
)
def get_cached_report(department: str) -> str:
    # VULNERABLE: no comprueba quien genero el informe ni quien lo pide.
    return _LAST_REPORT_CACHE.get(
        department, f"No hay ningun informe cacheado para el departamento '{department}'."
    )

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
