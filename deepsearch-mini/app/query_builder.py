"""Translates a structured query definition into SQL."""

MEASURES = {
    "average": "AVG(monthly_income)",
    "sum": "SUM(monthly_income)",
    "count": "COUNT(*)",
}

SUPPRESSION_THRESHOLD = {
    "average": 10,
    "sum": 10,
    "count": 5,
}


def suppress_rows(rows: list[dict], measure: str) -> list[dict]:
    """Hide values that are based on too few records.

    Each row must have 'group', 'value', and 'count' keys.
    Returns rows with value=None and suppressed=True where the threshold is not met.
    """
    threshold = SUPPRESSION_THRESHOLD[measure]
    result = []
    for row in rows:
        if row["count"] < threshold:
            result.append({"group": row["group"], "value": None, "suppressed": True})
        else:
            result.append({"group": row["group"], "value": row["value"]})
    return result


def build_query(q: dict) -> tuple[str, list]:
    """Build the SQL statement and its parameters for a query definition.

    Example definition:
        {
            "measure": "average",
            "filters": {"gender": "F", "city": "ירושלים", "ageFrom": 25, "ageTo": 35,
                        "yearFrom": 2021, "yearTo": 2024},
            "groupBy": "year"
        }
    """
    measure = MEASURES[q["measure"]]
    group_by = q.get("groupBy", "year")
    filters = q.get("filters", {})

    where = []
    params = []

    if filters.get("gender"):
        where.append("gender = ?")
        params.append(filters["gender"])

    if filters.get("city"):
        where.append("city = ?")
        params.append(filters["city"])

    if filters.get("ageFrom"):
        where.append("age >= ?")
        params.append(filters["ageFrom"])

    if filters.get("ageTo"):
        where.append("age <= ?")
        params.append(filters["ageTo"])

    if filters.get("yearFrom"):
        where.append("year >= ?")
        params.append(filters["yearFrom"])

    if filters.get("yearTo"):
        where.append("year <= ?")
        params.append(filters["yearTo"])

    sql = f"SELECT {group_by} AS grp, {measure} AS value, COUNT(monthly_income) AS count FROM person_year"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" GROUP BY {group_by} ORDER BY {group_by}"

    return sql, params


def render_sql(q: dict) -> str:
    """Return the query as one SQL string with the values inlined.

    Used when a query is saved, so it can be run again later exactly as it was.
    """
    sql, params = build_query(q)
    for value in params:
        literal = f"'{value}'" if isinstance(value, str) else str(value)
        sql = sql.replace("?", literal, 1)
    return sql
