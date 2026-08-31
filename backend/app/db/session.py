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


#: Columns added after the first release, as (table, column, definition).
#:
#: schema.sql uses CREATE TABLE IF NOT EXISTS, which silently does nothing when
#: the table already exists — so a new column in that file never reaches a
#: database that predates it. That matters here because the analysed database
#: ships with the repository: anyone cloning has a real database from day one,
#: and a schema change has to migrate it rather than assume a blank slate.
#:
#: Kept as a list rather than a migration framework because SQLite's ALTER TABLE
#: only supports adding columns, which is all this has ever needed. If a change
#: ever requires more, that is the signal to adopt Alembic — not before.
_ADDED_COLUMNS = [
    ("issue_clusters", "terms", "TEXT"),
]


def _migrate(conn: sqlite3.Connection) -> None:
    for table, column, definition in _ADDED_COLUMNS:
        existing = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        if existing and column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db() -> None:
    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    with conn:
        conn.executescript(SCHEMA_PATH.read_text())
        _migrate(conn)
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
