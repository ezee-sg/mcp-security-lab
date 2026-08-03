"""Verifica la integridad de las dependencias vendorizadas (ver tools/README.md)."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify_lockfile(lockfile_path: Path) -> list[str]:
    """Devuelve la lista de discrepancias encontradas (vacía si todo coincide)."""
    entries = json.loads(lockfile_path.read_text(encoding="utf-8"))
    mismatches = []
    for relative_path, expected_hash in entries.items():
        target = lockfile_path.parent / relative_path
        if not target.exists():
            mismatches.append(f"{relative_path}: fichero ausente")
            continue
        actual_hash = sha256_of(target)
        if actual_hash != expected_hash:
            mismatches.append(
                f"{relative_path}: hash no coincide "
                f"(esperado {expected_hash[:12]}..., obtenido {actual_hash[:12]}...)"
            )
    return mismatches

def main(argv: list[str]) -> int:
    if not argv:
        print("Uso: python verify_dependencies.py <dependencies.lock.json> [...]")
        return 2

    all_mismatches = []
    for arg in argv:
        lockfile_path = Path(arg)
        if not lockfile_path.exists():
            all_mismatches.append(f"{lockfile_path}: lockfile no encontrado (ejecuta generate_lockfile.py)")
            continue
        for mismatch in verify_lockfile(lockfile_path):
            all_mismatches.append(f"{lockfile_path}: {mismatch}")

    if all_mismatches:
        print("ALERTA: se han detectado dependencias manipuladas (Supply Chain / MCP04:2025):")
        for m in all_mismatches:
            print(f"  - {m}")
        return 1

    print(f"OK: {len(argv)} lockfile(s) verificados, sin discrepancias.")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
