"""Free-text question parsing.

In production this component calls an LLM that turns a free-text question
into the structured query definition used by the rest of the system.
For local development we use MockLLMParser, which imitates the LLM's output
with simple rules. Both implement the same interface, so the real LLM client
can replace the mock without touching the callers.
"""
import re
from typing import Protocol

CITIES = ["ירושלים", "תל אביב", "חיפה", "באר שבע", "אילת"]
GROUP_WORDS = {"שנה": "year", "שנים": "year", "מגדר": "gender", "עיר": "city", "ערים": "city"}


class QuestionParser(Protocol):
    def parse(self, text: str) -> dict:
        """Return a query definition: {"measure", "filters", "groupBy"}."""
        ...


class MockLLMParser:
    def parse(self, text: str) -> dict:
        filters = {}

        if "ממוצע" in text:
            measure = "average"
        elif "סך" in text or "סכום" in text:
            measure = "sum"
        else:
            measure = "count"

        if "נשים" in text:
            filters["gender"] = "F"
        elif "גברים" in text:
            filters["gender"] = "M"

        for city in CITIES:
            if city in text:
                filters["city"] = city

        ages = re.search(r"גילאי (\d+)\s*[-–]\s*(\d+)", text)
        if ages:
            filters["ageFrom"] = int(ages.group(1))
            filters["ageTo"] = int(ages.group(2))

        years = re.findall(r"20\d\d", text)
        if years:
            filters["yearFrom"] = int(min(years))
            filters["yearTo"] = int(max(years))

        group_by = "year"
        group = re.search(r"לפי (.+)$", text.strip())
        if group:
            word = group.group(1).strip(" .?")
            group_by = GROUP_WORDS.get(word, word)

        return {"measure": measure, "filters": filters, "groupBy": group_by}
