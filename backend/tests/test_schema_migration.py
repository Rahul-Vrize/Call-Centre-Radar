"""Guards the gap between schema.sql and a database that already exists.

`schema.sql` uses CREATE TABLE IF NOT EXISTS, which does nothing at all when the
table is already there. So adding a column to that file has no effect on any
existing database — and this project **ships its analysed database in the
repository**, which means every clone has a real database from day one and every
schema change is a migration whether or not it was written as one.

That bug has already happened once: `issue_clusters.terms` was added to
schema.sql, the code was updated to write it, and the batch died with
"table issue_clusters has no column named terms" against the shipped database.

These tests make the failure structural rather than remembered: the first
compares schema.sql against a database built the way a real one was — created
at an older revision, then migrated — and fails if any column is unreachable.
"""
import re
import sqlite3

import pytest

from app.db.session import SCHEMA_PATH, _ADDED_COLUMNS, _migrate


def declared_columns() -> dict[str, set[str]]:
    """Every table -> column set that schema.sql declares."""
    sql = SCHEMA_PATH.read_text()
    tables: dict[str, set[str]] = {}
    for match in re.finditer(
        r"CREATE TABLE IF NOT EXISTS\s+(\w+)\s*\((.*?)\n\);", sql, re.S
    ):
        table, body = match.group(1), match.group(2)
        cols = set()
        for line in body.splitlines():
            line = line.strip().rstrip(",")
            if not line or line.startswith("--"):
                continue
            first = line.split()[0]
            if first.upper() in {
                "PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT"
            }:
                continue
            cols.add(first)
        tables[table] = cols
    return tables


def test_schema_sql_is_parseable():
    tables = declared_columns()
    assert "calls" in tables
    assert "evidence" in tables
    assert "issue_clusters" in tables


def test_every_added_column_is_also_declared_in_schema_sql():
    """A migration entry with no matching column in schema.sql means a fresh
    clone and a migrated clone end up with different schemas."""
    declared = declared_columns()
    for table, column, _ in _ADDED_COLUMNS:
        assert table in declared, f"{table} is not declared in schema.sql"
        assert column in declared[table], (
            f"{table}.{column} is migrated onto existing databases but missing "
            f"from schema.sql — a fresh database would never get it"
        )


def test_a_database_created_before_the_column_gets_migrated(tmp_path):
    """The real scenario: a database that predates a column must reach the same
    schema as a fresh one after `_migrate` runs."""
    if not _ADDED_COLUMNS:
        pytest.skip("no post-release columns to check")

    db = tmp_path / "old.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row

    # Build the schema, then drop the newer columns back out to simulate a
    # database created at an earlier revision. SQLite cannot DROP COLUMN on old
    # versions, so rebuild the table without them instead.
    conn.executescript(SCHEMA_PATH.read_text())
    for table, column, _ in _ADDED_COLUMNS:
        cols = [
            r["name"] for r in conn.execute(f"PRAGMA table_info({table})")
            if r["name"] != column
        ]
        conn.execute(f"CREATE TABLE _old AS SELECT {', '.join(cols)} FROM {table}")
        conn.execute(f"DROP TABLE {table}")
        conn.execute(f"ALTER TABLE _old RENAME TO {table}")

    for table, column, _ in _ADDED_COLUMNS:
        present = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        assert column not in present, "setup failed to produce an older schema"

    _migrate(conn)

    for table, column, _ in _ADDED_COLUMNS:
        present = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        assert column in present, f"_migrate did not add {table}.{column}"
    conn.close()


def test_migrate_is_idempotent(tmp_path):
    """It runs on every boot, so running twice must not raise."""
    db = tmp_path / "fresh.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_PATH.read_text())
    _migrate(conn)
    _migrate(conn)  # would raise "duplicate column name" if unguarded
    conn.close()
