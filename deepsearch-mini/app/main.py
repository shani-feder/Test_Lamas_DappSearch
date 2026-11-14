"""Deep Search mini - HTTP API."""
from fastapi import FastAPI

from app import db, free_text, saved_queries
from app.phrasing import describe
from app.query_builder import MEASURES
from app.query_runner import execute_query

app = FastAPI(title="Deep Search mini")


@app.post("/api/query/run")
def run_query(q: dict):
    """Run a structured query definition."""
    if q.get("measure") not in MEASURES:
        return {"question": "", "rows": []}
    return {
        "question": describe(q),
        "rows": execute_query(q),
    }


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
