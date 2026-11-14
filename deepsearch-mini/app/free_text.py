"""Free-text questions: the LLM turns the question into a query, and we compute the answer."""
from app.llm_parser import MockLLMParser
from app.phrasing import describe
from app.query_runner import execute_query

parser = MockLLMParser()


def answer(text: str) -> dict:
    """Answer a free-text question."""
    q = parser.parse(text)
    return {"question": describe(q), "interpreted": q, "rows": execute_query(q)}
