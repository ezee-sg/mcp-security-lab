"""Inicialización y semilla de la base de datos SQLite del departamento de Finanzas."""
from __future__ import annotations
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "finanzas.db")

INVOICES = [
    (1, "Cloudtec Hosting S.L.", 4200.50, "paid", "2026-01-12"),
    (2, "Oficinas Sevilla Centro", 1800.00, "paid", "2026-01-20"),
    (3, "Consultora Delta", 9500.00, "pending", "2026-02-03"),
    (4, "Suministros Informáticos Betis", 620.75, "paid", "2026-02-10"),
    (5, "Consultora Delta", 3100.00, "overdue", "2026-01-05"),
    (6, "Cloudtec Hosting S.L.", 4200.50, "paid", "2026-02-12"),
]

# Copia local (no autoritativa) usada por RRHH->Finanzas para nóminas.
EMPLOYEES = [
    (1, "Ana García Ruiz", 28500, "rrhh"),
    (2, "Luis Pérez Molina", 41200, "rrhh"),
    (3, "Marta Ruiz Campos", 32100, "finanzas"),
    (4, "Carlos Soto Vega", 47800, "finanzas"),
    (5, "Elena Vidal Torres", 39500, "it"),
    (6, "Javier León Ortiz", 26800, "it"),
    (7, "Sofía Reyes Alba", 89000, "direccion"),
]

def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY,
            vendor TEXT NOT NULL,
            amount REAL NOT NULL,
            status TEXT NOT NULL,
            date TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            salary REAL NOT NULL,
            department TEXT NOT NULL
        )
        """
    )
    cursor.execute("SELECT COUNT(*) FROM invoices")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO invoices VALUES (?, ?, ?, ?, ?)", INVOICES)
    cursor.execute("SELECT COUNT(*) FROM employees")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO employees VALUES (?, ?, ?, ?)", EMPLOYEES)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print(f"Base de datos de Finanzas inicializada en {DB_PATH}")
