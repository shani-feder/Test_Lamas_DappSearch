"""SQLite access layer.

Loads the sample data set (data/person_year.csv) into an in-memory database
when the application starts.
"""
import csv
import sqlite3
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "person_year.csv"

_SCHEMA = """
CREATE TABLE person_year (
    id             INTEGER PRIMARY KEY,
    year           INTEGER NOT NULL,
    gender         TEXT    NOT NULL,   -- F / M
    age            INTEGER NOT NULL,
    city           TEXT    NOT NULL,
    employed       INTEGER NOT NULL,   -- 0 / 1
    monthly_income REAL                -- NULL when not employed
);
"""


def _load() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute(_SCHEMA)
    with DATA_FILE.open(encoding="utf-8", newline="") as f:
        rows = [
            (
                int(r["id"]),
                int(r["year"]),
                r["gender"],
                int(r["age"]),
                r["city"],
                int(r["employed"]),
                float(r["monthly_income"]) if r["monthly_income"] else None,
            )
            for r in csv.DictReader(f)
        ]
    conn.executemany("INSERT INTO person_year VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
    conn.commit()
    return conn


_conn = _load()


def execute(sql: str, params=()) -> list:
    """Run a query and return all rows."""
    return _conn.execute(sql, params).fetchall()
