"""Servidor de escucha para los escenarios de exfiltración"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

app = FastAPI(title="Exfil Listener (laboratorio Hispalis Technologies)")

BASE_DIR = Path(__file__).parent
LOG_PATH = BASE_DIR / "collected.log"
DASHBOARD_PATH = BASE_DIR / "static" / "dashboard.html"

_events: list[dict] = []

def _load_existing_events() -> None:
    if not LOG_PATH.exists():
        return
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                _events.append(json.loads(line))
            except json.JSONDecodeError:
                continue

_load_existing_events()

@app.get("/api/health")
def health() -> dict:
    return {"status": "listening", "service": "exfil-listener", "captured": len(_events)}

@app.get("/api/events")
def list_events() -> list[dict]:
    return list(reversed(_events))

@app.delete("/api/events")
def clear_events() -> dict:
    _events.clear()
    LOG_PATH.write_text("", encoding="utf-8")
    return {"status": "cleared"}

@app.post("/collect")
async def collect(request: Request) -> dict:
    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError):
        raw = await request.body()
        payload = {"raw_body": raw.decode("utf-8", errors="replace")}

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_ip": request.client.host if request.client else "unknown",
        "payload": payload,
    }

    print(f"[EXFIL-LISTENER] Datos recibidos: {json.dumps(entry, ensure_ascii=False)}")
    _events.append(entry)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return {"status": "received"}

@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return DASHBOARD_PATH.read_text(encoding="utf-8")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8888)
