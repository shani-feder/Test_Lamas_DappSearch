"""Deep Search mini - HTTP API."""
from fastapi import FastAPI

from app import db, free_text, saved_queries
from app.phrasing import describe
from app.query_builder import build_query

app = FastAPI(title="Deep Search mini")


@app.post("/api/query/run")
def run_query(q: dict):
    """Run a structured query definition."""
    try:
        sql, params = build_query(q)
        rows = db.execute(sql, params)
        return {
            "question": describe(q),
            "rows": [{"group": str(row[0]), "value": row[1]} for row in rows],
        }
    except Exception:
        print("query failed")
        return {"question": "", "rows": []}


@app.post("/api/ask")
def ask(body: dict):
    """Answer a free-text question."""
    return free_text.answer(body["text"])


@app.get("/api/saved")
def list_saved():
    """List the saved queries."""
    return saved_queries.list_saved()


@app.post("/api/saved")
def save_query(body: dict):
    """Save a query definition under a name."""
    return saved_queries.save(body["name"], body["owner"], body["query"])


@app.post("/api/saved/{saved_id}/run")
def run_saved(saved_id: int):
    """Run a saved query."""
    return saved_queries.run(saved_id)


@app.get("/api/health")
def health():
    return {"status": "ok"}
