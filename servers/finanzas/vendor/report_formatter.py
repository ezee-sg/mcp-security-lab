"""Formateador de informes de nómina: dependencia "vendorizada"."""
from __future__ import annotations


def format_salary_report(rows: list[tuple]) -> str:
    lines = ["INFORME DE NOMINA - Hispalis Technologies", "-" * 46]
    for name, salary, department in rows:
        lines.append(f"{name:<28} {department:<12} {salary:>10,.2f} EUR")
    return "\n".join(lines)
