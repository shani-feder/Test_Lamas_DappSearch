"""Executes a query definition and applies suppression."""
from app import db
from app.query_builder import build_query, suppress_rows


def execute_query(q: dict) -> list[dict]:
    sql, params = build_query(q)
    rows = db.execute(sql, params)
    raw = [{"group": str(row[0]), "value": row[1], "count": row[2]} for row in rows]
    return suppress_rows(raw, q["measure"])
