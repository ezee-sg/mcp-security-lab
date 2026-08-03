"""Servidor MCP de Finanzas — VERSIÓN ENDURECIDA (ver servers/README.md)."""
from __future__ import annotations

import os
import re
import sqlite3
import sys
from typing import Literal, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, field_validator

from common.auth import require_role
from common.logging_utils import log_tool_call
from common.session import get_or_create_session

from database import DB_PATH, init_db
from vendor.report_formatter import format_salary_report

init_db()

MCP_HTTP_HOST = os.environ.get("MCP_HTTP_HOST", "127.0.0.1")
MCP_HTTP_PORT = int(os.environ.get("MCP_HTTP_PORT", "9012"))

mcp = FastMCP(
    "Hispalis Finanzas (hardened)",
    instructions="Servidor MCP del departamento de Finanzas de Hispalis Technologies.",
    host=MCP_HTTP_HOST,
    port=MCP_HTTP_PORT,
    streamable_http_path="/mcp",
)

class InvoiceFilter(BaseModel):
    status: Literal["paid", "pending", "overdue"]
    vendor: Optional[str] = None

    @field_validator("vendor")
    @classmethod
    def validate_vendor(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r"^[a-zA-Z0-9 \-\.]{1,100}$", v):
            raise ValueError("Nombre de proveedor invalido.")
        return v

@mcp.tool(
    description=(
        "Consulta facturas de la base de datos. Acepta un filtro estructurado por "
        "estado (paid, pending, overdue) y opcionalmente por proveedor."
    )
)
def query_invoices(filter: InvoiceFilter, session_token: str) -> str:
    try:
        payload = require_role(session_token, "dept_manager", "it_admin", "director")
    except PermissionError as exc:
        log_tool_call("fin.query_invoices", {"filter": filter.model_dump()}, "unknown", str(exc), False)
        raise

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if filter.vendor:
        query = "SELECT * FROM invoices WHERE status = ? AND vendor = ?"
        params = (filter.status, filter.vendor)
    else:
        query = "SELECT * FROM invoices WHERE status = ?"
        params = (filter.status,)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    result = str(rows)
    log_tool_call("fin.query_invoices", {"filter": filter.model_dump()}, payload["role"], result, True)
    return result

@mcp.tool(
    description="Genera un informe de nominas por departamento ('all' para todos los departamentos)."
)
def get_salary_report(department: str, session_token: str) -> str:
    try:
        payload = require_role(session_token, "dept_manager", "it_admin", "director")
    except PermissionError as exc:
        log_tool_call("fin.get_salary_report", {"department": department}, "unknown", str(exc), False)
        raise

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if payload["role"] == "dept_manager":
        # dept_manager solo ve su propio departamento, pida lo que pida.
        cursor.execute(
            "SELECT name, salary, department FROM employees WHERE department = ?",
            (payload["department"],),
        )
    elif department == "all":
        cursor.execute("SELECT name, salary, department FROM employees")
    else:
        cursor.execute(
            "SELECT name, salary, department FROM employees WHERE department = ?",
            (department,),
        )
    rows = cursor.fetchall()
    conn.close()

    result = format_salary_report(rows)

    # Caché aislada por usuario (ver servers/README.md), no global.
    session = get_or_create_session(payload["sub"], payload["role"])
    session.cache_set("last_report", result)

    log_tool_call("fin.get_salary_report", {"department": department}, payload["role"], result, True)
    return result

@mcp.tool(
    description=(
        "Devuelve el ultimo informe de nomina generado por el propio usuario en esta "
        "sesion, sin necesidad de volver a consultarlo."
    )
)
def get_cached_report(session_token: str) -> str:
    try:
        payload = require_role(session_token, "dept_manager", "it_admin", "director")
    except PermissionError as exc:
        log_tool_call("fin.get_cached_report", {}, "unknown", str(exc), False)
        raise

    session = get_or_create_session(payload["sub"], payload["role"])
    result = session.cache_get("last_report") or "No tienes ningun informe cacheado en esta sesion."

    log_tool_call("fin.get_cached_report", {}, payload["role"], result, True)
    return result

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
