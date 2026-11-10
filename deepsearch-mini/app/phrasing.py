"""Builds a readable Hebrew sentence that describes a query definition."""

MEASURE_TEXT = {
    "average": "השכר הממוצע",
    "sum": "סך השכר",
    "count": "מספר הרשומות",
}
GENDER_TEXT = {"F": "נשים", "M": "גברים"}
GROUP_TEXT = {"year": "שנה", "gender": "מגדר", "city": "עיר"}


def describe(q: dict) -> str:
    filters = q.get("filters", {})
    parts = [MEASURE_TEXT.get(q.get("measure"), str(q.get("measure")))]
    parts.append("של " + GENDER_TEXT.get(filters.get("gender"), "כלל האוכלוסייה"))

    if filters.get("ageFrom") and filters.get("ageTo"):
        parts.append(f"בגילאי {filters['ageFrom']}-{filters['ageTo']}")

    if filters.get("city"):
        parts.append("ב" + filters["city"])

    year_from, year_to = filters.get("yearFrom"), filters.get("yearTo")
    if year_from and year_to:
        if year_from == year_to:
            parts.append(f"בשנת {year_from}")
        else:
            parts.append(f"בין השנים {year_from}-{year_to}")

    group = q.get("groupBy", "year")
    return " ".join(parts) + f", בחלוקה לפי {GROUP_TEXT.get(group, group)}."
