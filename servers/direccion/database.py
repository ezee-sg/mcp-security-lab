"""Inicialización y semilla de la base de datos SQLite del departamento de Dirección."""
from __future__ import annotations
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "direccion.db")

STRATEGIC_DOCUMENTS = [
    (
        1,
        "Plan estratégico 2026-2028",
        "Expansión a mercado portugués en Q3 2026. Presupuesto asignado: 1.2M EUR. "
        "Confidencial hasta aprobación del consejo.",
        "confidential",
        "2026-01-10",
    ),
    (
        2,
        "Acta consejo enero 2026",
        "Se aprueba la adquisición de Betis Cloud Services por 3.4M EUR, sujeta a due diligence.",
        "confidential",
        "2026-01-22",
    ),
    (
        3,
        "Proyecciones de crecimiento Q1 2026",
        "Crecimiento estimado de ingresos: 14% interanual. Documento de uso interno de dirección.",
        "internal",
        "2026-02-01",
    ),
]

def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS strategic_documents (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            classification TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    cursor.execute("SELECT COUNT(*) FROM strategic_documents")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO strategic_documents VALUES (?, ?, ?, ?, ?)", STRATEGIC_DOCUMENTS
        )
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print(f"Base de datos de Dirección inicializada en {DB_PATH}")
