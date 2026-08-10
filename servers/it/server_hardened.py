"""Servidor MCP de IT — VERSIÓN hardened (ver servers/README.md)."""
from __future__ import annotations
import os
import sqlite3
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import httpx
from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel

from common.auth import require_role
from common.logging_utils import log_tool_call
from common.sanitize import redact_secrets, sanitize_untrusted_text

from database import DB_PATH, init_db, insert_ticket

init_db()

class ConfirmationSchema(BaseModel):
    confirm: bool

CONFIGS_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "configs"))
RUGPULL_FLAG_PATH = os.path.join(os.path.dirname(__file__), ".rugpull_active")
RUGPULL_COLLECTOR_URL = os.environ.get("EXFIL_LISTENER_URL", "http://127.0.0.1:8888/collect")

# Whitelist deliberada: NO incluye el puerto 8888, el exfil-listener (ver servers/README.md).
ALLOWED_EMAIL_DOMAIN = "hispalis.tech"
ALLOWED_WEBHOOK_NETLOCS = {"127.0.0.1:9000", "localhost:9000"}

MCP_HTTP_HOST = os.environ.get("MCP_HTTP_HOST", "127.0.0.1")
MCP_HTTP_PORT = int(os.environ.get("MCP_HTTP_PORT", "9013"))

mcp = FastMCP(
    "Hispalis IT (hardened)",
    instructions="Servidor MCP del departamento de IT de Hispalis Technologies.",
    host=MCP_HTTP_HOST,
    port=MCP_HTTP_PORT,
    streamable_http_path="/mcp",
)

def _is_allowed_destination(to: str) -> bool:
    if to.startswith("http://") or to.startswith("https://"):
        url = httpx.URL(to)
        netloc = f"{url.host}:{url.port}" if url.port else str(url.host)
        return netloc in ALLOWED_WEBHOOK_NETLOCS
    return to.endswith(f"@{ALLOWED_EMAIL_DOMAIN}")

@mcp.tool(
    description="Lee un fichero de configuracion del servidor a partir de su ruta relativa."
)
def read_config(path: str, session_token: str) -> str:
    try:
        payload = require_role(session_token, "dept_manager", "it_admin", "director")
    except PermissionError as exc:
        log_tool_call("it.read_config", {"path": path}, "unknown", str(exc), False)
        raise

    requested = os.path.realpath(os.path.join(CONFIGS_DIR, path))
    if not (requested == CONFIGS_DIR or requested.startswith(CONFIGS_DIR + os.sep)):
        result = "Acceso a ruta no permitida."
        log_tool_call("it.read_config", {"path": path}, payload["role"], result, False)
        raise ValueError(result)

    try:
        with open(requested, "r", encoding="utf-8", errors="replace") as f:
            content = redact_secrets(f.read())
    except OSError as exc:
        result = f"Error leyendo fichero: {exc}"
        log_tool_call("it.read_config", {"path": path}, payload["role"], result, False)
        return result

    log_tool_call("it.read_config", {"path": path}, payload["role"], content, True)
    return content

@mcp.tool(
    description=(
        "Envia una notificacion a un destinatario. Acepta una direccion de email o una "
        "URL de webhook como destino."
    )
)
async def send_notification(ctx: Context, to: str, subject: str, body: str, session_token: str) -> str:
    try:
        payload = require_role(
            session_token, "employee", "dept_manager", "it_admin", "director"
        )
    except PermissionError as exc:
        log_tool_call("it.send_notification", {"to": to}, "unknown", str(exc), False)
        raise

    if not _is_allowed_destination(to):
        result = f"Destino '{to}' no esta en la whitelist de notificaciones permitidas. Operacion bloqueada."
        log_tool_call("it.send_notification", {"to": to, "subject": subject}, payload["role"], result, False)
        return result

    confirmation = await ctx.elicit(
        message=f"¿Confirmar el envio de una notificacion a '{to}' con asunto '{subject}'?",
        schema=ConfirmationSchema,
    )
    if confirmation.action != "accept" or not confirmation.data.confirm:
        result = "Operacion cancelada por el usuario (HITL)."
        log_tool_call("it.send_notification", {"to": to, "subject": subject}, payload["role"], result, False)
        return result

    if to.startswith("http://") or to.startswith("https://"):
        try:
            resp = httpx.post(to, json={"subject": subject, "body": body}, timeout=5)
            result = f"Notificacion enviada a {to} (status {resp.status_code})"
        except httpx.HTTPError as exc:
            result = f"Error enviando notificacion a {to}: {exc}"
    else:
        result = f"Notificacion enviada por email a {to}: [{subject}] {body[:80]}"

    # La whitelist ya bloquea destinos externos; esto es solo deteccion/alerta (ver escenario 03).
    if os.path.exists(RUGPULL_FLAG_PATH):
        log_tool_call(
            "it.send_notification",
            {"to": to},
            payload["role"],
            "ALERTA: comportamiento de la tool difiere de la version verificada (posible Rug Pull).",
            False,
        )

    log_tool_call("it.send_notification", {"to": to, "subject": subject}, payload["role"], result, True)
    return result

@mcp.tool(
    description=(
        "Abre un ticket de soporte tecnico en nombre de un usuario o cliente externo. "
        "No requiere autenticacion: cualquiera puede abrir un ticket (igual que en la "
        "version vulnerable). La proteccion frente a contenido malicioso ocurre al leer "
        "el ticket (ver it://tickets/latest), no al crearlo."
    )
)
def create_ticket(subject: str, body: str, requester: str) -> str:
    ticket_id = insert_ticket(subject, body, requester, datetime.now().isoformat())
    log_tool_call("it.create_ticket", {"subject": subject, "requester": requester}, "anonymous", f"ticket #{ticket_id}", True)
    return f"Ticket #{ticket_id} creado correctamente."

@mcp.resource(
    "it://tickets/latest",
    description="Ultimos tickets de soporte abiertos.",
)
def latest_tickets() -> str:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, subject, body, requester, created_at FROM tickets ORDER BY id DESC LIMIT 5"
    )
    rows = cursor.fetchall()
    conn.close()
    blocks = [
        f"Ticket #{r[0]} - {r[1]} (de {r[3]}, {r[4]})\n{sanitize_untrusted_text(r[2])}" for r in rows
    ]
    return "\n---\n".join(blocks)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
