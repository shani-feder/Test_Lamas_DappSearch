"""Saved queries: a user saves a query under a name and runs it again later."""
import json
from pathlib import Path

from app import db
from app.query_builder import build_query, suppress_rows
from app.query_runner import execute_query

STORE = Path(__file__).resolve().parent.parent / "data" / "saved_queries.json"


def _load() -> list:
    return json.loads(STORE.read_text(encoding="utf-8"))


def _write(items: list) -> None:
    STORE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def list_saved() -> list:
    return [{"id": item["id"], "owner": item["owner"], "name": item["name"]} for item in _load()]


def save(name: str, owner: str, query: dict) -> dict:
    items = _load()
    item = {
        "id": max((item["id"] for item in items), default=0) + 1,
        "owner": owner,
        "name": name,
        "query": query,
    }
    items.append(item)
    _write(items)
    return {"id": item["id"], "owner": owner, "name": name}


def run(saved_id: int) -> dict:
    item = next(item for item in _load() if item["id"] == saved_id)
    return {
        "name": item["name"],
        "rows": execute_query(item["query"]),
    }
