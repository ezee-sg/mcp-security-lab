"""Detecta servidores MCP no registrados en servers/registry.json (ver tools/README.md)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVERS_DIR = REPO_ROOT / "servers"
REGISTRY_PATH = SERVERS_DIR / "registry.json"

def discover_server_dirs() -> list[str]:
    return sorted(
        p.name
        for p in SERVERS_DIR.iterdir()
        if p.is_dir() and (p / "server.py").exists()
    )

def load_approved_names() -> set[str]:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {entry["name"] for entry in registry["approved_servers"]}

def main() -> int:
    discovered = discover_server_dirs()
    approved = load_approved_names()

    shadow = [name for name in discovered if name not in approved]

    print(f"Servidores MCP encontrados en servers/: {discovered}")
    print(f"Servidores aprobados en registry.json:   {sorted(approved)}")

    if shadow:
        print("\nALERTA: se han detectado Shadow MCP Servers (OWASP MCP09:2025):")
        for name in shadow:
            print(f"  - servers/{name}/server.py NO figura en servers/registry.json")
        return 1

    print("\nOK: todos los servidores MCP presentes están registrados y aprobados.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
