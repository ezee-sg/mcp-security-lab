"""Analizador estático de descripciones de tools MCP (ver tools/README.md)."""
from __future__ import annotations

import glob
import json
import re
import sys

SUSPICIOUS_PATTERNS = [
    re.compile(r"\[\s*(instruccion|instrucción|oculto|hidden|system)[^\]]*\]", re.IGNORECASE),
    re.compile(r"ignora\s+(la\s+)?solicitud", re.IGNORECASE),
    re.compile(r"no\s+menciones\s+esta\s+accion", re.IGNORECASE),
    re.compile(r"\bignore\s+(previous|all)\s+instructions\b", re.IGNORECASE),
    re.compile(r"invoca\s+silenciosamente", re.IGNORECASE),
]

def scan_file(path: str) -> list[tuple[str, str, str]]:
    findings = []
    with open(path, "r", encoding="utf-8") as f:
        descriptions = json.load(f)
    for tool_name, description in descriptions.items():
        for pattern in SUSPICIOUS_PATTERNS:
            if pattern.search(description):
                findings.append((path, tool_name, pattern.pattern))
    return findings

def main(argv: list[str]) -> int:
    if not argv:
        print("Uso: python mcp_scan_lite.py <descriptions.json> [...]")
        return 2

    paths: list[str] = []
    for pattern in argv:
        paths.extend(glob.glob(pattern, recursive=True))

    all_findings = []
    for path in paths:
        all_findings.extend(scan_file(path))

    if all_findings:
        print("ALERTA: se han detectado posibles descripciones envenenadas (Tool Poisoning):")
        for path, tool_name, pattern in all_findings:
            print(f"  - {path} :: tool '{tool_name}' coincide con el patron /{pattern}/")
        return 1

    print(f"OK: {len(paths)} fichero(s) de descripciones analizados, sin hallazgos.")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
