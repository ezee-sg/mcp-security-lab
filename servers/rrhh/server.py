"""Servidor MCP de RRHH — VERSIÓN VULNERABLE (ver servers/README.md)."""
from __future__ import annotations

import json
import os
import sqlite3

from mcp.server.fastmcp import FastMCP

from database import DB_PATH, init_db

DESCRIPTIONS_PATH = os.path.join(os.path.dirname(__file__), "descriptions.json")
with open(DESCRIPTIONS_PATH, "r", encoding="utf-8") as f:
    DESCRIPTIONS = json.load(f)

init_db()

MCP_HTTP_HOST = os.environ.get("MCP_HTTP_HOST", "127.0.0.1")
MCP_HTTP_PORT = int(os.environ.get("MCP_HTTP_PORT", "9001"))

mcp = FastMCP(
    "Hispalis RRHH (vulnerable)",
    instructions="Servidor MCP del departamento de Recursos Humanos de Hispalis Technologies.",
    host=MCP_HTTP_HOST,
    port=MCP_HTTP_PORT,
    streamable_http_path="/mcp",
)


@mcp.tool(description=DESCRIPTIONS["get_employee"])
def get_employee(employee_id: int) -> str:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, position, department, email, salary, hire_date FROM employees WHERE id = ?",
        (employee_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return f"No existe ningun empleado con id {employee_id}."
    keys = ["id", "name", "position", "department", "email", "salary", "hire_date"]
    return json.dumps(dict(zip(keys, row)), ensure_ascii=False)


@mcp.tool(description=DESCRIPTIONS["list_employees"])
def list_employees() -> str:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, position, department, email, salary FROM employees")
    rows = cursor.fetchall()
    conn.close()
    keys = ["id", "name", "position", "department", "email", "salary"]
    return json.dumps([dict(zip(keys, row)) for row in rows], ensure_ascii=False)


@mcp.resource("hr://organigrama", description="Organigrama de Hispalis Technologies.")
def organigrama() -> str:
    return (
        "Sofía Reyes Alba (Directora General)\n"
        "├── Luis Pérez Molina (Responsable de RRHH)\n"
        "│   └── Ana García Ruiz (Técnica de RRHH)\n"
        "├── Carlos Soto Vega (Responsable de Finanzas)\n"
        "│   └── Marta Ruiz Campos (Analista Financiera)\n"
        "└── Elena Vidal Torres (Administradora IT)\n"
        "    └── Javier León Ortiz (Técnico de Soporte IT)\n"
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
