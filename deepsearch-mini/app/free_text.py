"""Free-text questions: the LLM turns the question into a query, and we compute the answer."""
from collections import defaultdict

from app import db
from app.llm_parser import MockLLMParser
from app.phrasing import describe

parser = MockLLMParser()

# filter name -> (column, operator)
FILTERS = {
    "gender": ("gender", "="),
    "city": ("city", "="),
    "ageFrom": ("age", ">="),
    "ageTo": ("age", "<="),
    "yearFrom": ("year", ">="),
    "yearTo": ("year", "<="),
}


def answer(text: str) -> dict:
    """Answer a free-text question."""
    q = parser.parse(text)

    conditions = ["1 = 1"]
    params = []
    for name, value in q["filters"].items():
        column, operator = FILTERS[name]
        conditions.append(f"{column} {operator} ?")
        params.append(value)

    group_by = q["groupBy"]
    rows = db.execute(
        f"SELECT {group_by}, monthly_income FROM person_year WHERE {' AND '.join(conditions)}",
        params,
    )

    groups = defaultdict(list)
    for key, income in rows:
        groups[key].append(income)

    result = []
    for key in sorted(groups):
        incomes = groups[key]
        if q["measure"] == "average":
            value = sum(income or 0 for income in incomes) / len(incomes)
        elif q["measure"] == "sum":
            value = sum(income or 0 for income in incomes)
        else:
            value = len(incomes)
        result.append({"group": str(key), "value": value})

    return {"question": describe(q), "interpreted": q, "rows": result}
