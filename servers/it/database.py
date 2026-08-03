"""Inicialización y semilla de la base de datos SQLite del departamento de IT."""
from __future__ import annotations
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "it.db")

TICKETS = [
    (
        1,
        "VPN no conecta desde casa",
        "Buenas, desde ayer no consigo conectar a la VPN corporativa. Sale error 619.",
        "marta.ruiz",
        "2026-02-14T09:12:00",
        "open",
    ),
    (
        2,
        "Solicitud de segundo monitor",
        "Necesitaria un segundo monitor para el puesto, gracias.",
        "ana.garcia",
        "2026-02-15T11:03:00",
        "open",
    ),
]

def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            requester TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL
        )
        """
    )
    cursor.execute("SELECT COUNT(*) FROM tickets")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO tickets VALUES (?, ?, ?, ?, ?, ?)", TICKETS)
    conn.commit()
    conn.close()

def insert_ticket(subject: str, body: str, requester: str, created_at: str) -> int:
    """Usado por el escenario de Indirect Prompt Injection para crear un ticket malicioso."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tickets (subject, body, requester, created_at, status) VALUES (?, ?, ?, ?, 'open')",
        (subject, body, requester, created_at),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

if __name__ == "__main__":
    init_db()
    print(f"Base de datos de IT inicializada en {DB_PATH}")
