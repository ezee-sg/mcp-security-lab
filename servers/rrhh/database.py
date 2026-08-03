"""Inicialización y semilla de la base de datos SQLite del departamento de RRHH."""
from __future__ import annotations
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "rrhh.db")

EMPLOYEES = [
    (1, "Ana García Ruiz", "Técnica de RRHH", "rrhh", "ana.garcia@hispalis.tech", 28500, "2021-03-01", None),
    (2, "Luis Pérez Molina", "Responsable de RRHH", "rrhh", "luis.perez@hispalis.tech", 41200, "2019-06-15", None),
    (3, "Marta Ruiz Campos", "Analista Financiera", "finanzas", "marta.ruiz@hispalis.tech", 32100, "2022-01-10", 4),
    (4, "Carlos Soto Vega", "Responsable de Finanzas", "finanzas", "carlos.soto@hispalis.tech", 47800, "2018-09-01", None),
    (5, "Elena Vidal Torres", "Administradora IT", "it", "elena.vidal@hispalis.tech", 39500, "2020-02-20", None),
    (6, "Javier León Ortiz", "Técnico de Soporte IT", "it", "javier.leon@hispalis.tech", 26800, "2023-04-11", 5),
    (7, "Sofía Reyes Alba", "Directora General", "direccion", "sofia.reyes@hispalis.tech", 89000, "2016-01-05", None),
]

def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            position TEXT NOT NULL,
            department TEXT NOT NULL,
            email TEXT NOT NULL,
            salary REAL NOT NULL,
            hire_date TEXT NOT NULL,
            manager_id INTEGER
        )
        """
    )
    cursor.execute("SELECT COUNT(*) FROM employees")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO employees VALUES (?, ?, ?, ?, ?, ?, ?, ?)", EMPLOYEES
        )
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print(f"Base de datos de RRHH inicializada en {DB_PATH}")
