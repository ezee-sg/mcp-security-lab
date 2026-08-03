"""Genera dependencies.lock.json a partir de las dependencias vendorizadas (ver tools/README.md)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# lockfile -> ficheros vendorizados que cubre
LOCKFILES: dict[Path, list[Path]] = {
    REPO_ROOT / "servers" / "finanzas" / "dependencies.lock.json": [
        REPO_ROOT / "servers" / "finanzas" / "vendor" / "report_formatter.py",
    ],
}

def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> None:
    for lockfile_path, files in LOCKFILES.items():
        entries = {str(f.relative_to(lockfile_path.parent).as_posix()): sha256_of(f) for f in files}
        lockfile_path.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Actualizado {lockfile_path.relative_to(REPO_ROOT)} con {len(entries)} entrada(s).")

if __name__ == "__main__":
    main()
