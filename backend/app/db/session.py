"""SQLite connection helper. One file database — no server to run, per the
brief's "how you store the analysis is your design decision" latitude."""
import sqlite3
from pathlib import Path
from typing import Annotated, Iterator

from fastapi import Depends

from app.config import settings

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    # The batch writes while the API reads; without this, a concurrent reader
    # raises "database is locked" instead of waiting the moment out.
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn


def init_db() -> None:
    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    with conn:
        conn.executescript(SCHEMA_PATH.read_text())
    conn.close()


def get_db() -> Iterator[sqlite3.Connection]:
    """Request-scoped connection. SQLite connections are not thread-safe and
    FastAPI may serve requests on different threads, so one per request."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


#: Use as `conn: DbConn` in a route signature.
DbConn = Annotated[sqlite3.Connection, Depends(get_db)]
