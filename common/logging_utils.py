from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("hispalis.audit")

AUDIT_LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "audit.log"
SENSITIVE_KEYS = {"password", "salary", "session_token", "ssn", "iban", "secret"}

def redact_sensitive(params: dict) -> dict:
    redacted = {}
    for key, value in params.items():
        if key.lower() in SENSITIVE_KEYS or "token" in key.lower():
            redacted[key] = "***REDACTED***"
        else:
            redacted[key] = value
    return redacted

def log_tool_call(tool_name: str, params: dict, user_role: str, result: str, success: bool) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool": tool_name,
        "role": user_role,
        "params": redact_sensitive(params),
        "success": success,
        "result_preview": (result[:100] if success and result else result or ""),
    }
    line = json.dumps(entry, ensure_ascii=False)
    logger.info(line)

    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
