"""SQLite connection helper. One file database — no server to run, per the
brief's "how you store the analysis is your design decision" latitude."""
import sqlite3
from pathlib import Path

from app.config import settings

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    with conn:
        conn.executescript(SCHEMA_PATH.read_text())
    conn.close()
