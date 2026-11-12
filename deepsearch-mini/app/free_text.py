"""Free-text questions: the LLM turns the question into a query, and we compute the answer."""
from app import db
from app.llm_parser import MockLLMParser
from app.phrasing import describe
from app.query_builder import build_query, suppress_rows

parser = MockLLMParser()


def answer(text: str) -> dict:
    """Answer a free-text question."""
    q = parser.parse(text)
    sql, params = build_query(q)
    rows = db.execute(sql, params)
    raw = [{"group": str(row[0]), "value": row[1], "count": row[2]} for row in rows]
    return {"question": describe(q), "interpreted": q, "rows": suppress_rows(raw, q["measure"])}
