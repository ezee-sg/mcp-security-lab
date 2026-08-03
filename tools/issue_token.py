"""CLI de login: emite un session_token de prueba para un usuario (ver tools/README.md)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.auth import USERS, issue_token

def main(argv: list[str]) -> int:
    if not argv:
        print("Uso: python tools/issue_token.py <usuario>")
        print(f"Usuarios disponibles: {', '.join(USERS)}")
        return 2

    username = argv[0]
    if username not in USERS:
        print(f"Usuario desconocido: {username}")
        print(f"Usuarios disponibles: {', '.join(USERS)}")
        return 1

    role, department, employee_id = USERS[username]
    token = issue_token(username)
    print(f"Usuario: {username}  (rol={role}, departamento={department}, employee_id={employee_id})")
    print("session_token:")
    print(token)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
