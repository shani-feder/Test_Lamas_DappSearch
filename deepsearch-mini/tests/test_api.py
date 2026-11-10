from fastapi.testclient import TestClient

from app import db, saved_queries
from app.main import app
from app.query_builder import MEASURES, build_query

client = TestClient(app)

EXAMPLE = {
    "measure": "average",
    "filters": {"gender": "F", "city": "ירושלים", "ageFrom": 25, "ageTo": 35,
                "yearFrom": 2021, "yearTo": 2024},
    "groupBy": "year",
}


def test_average_income_by_year():
    response = client.post("/api/query/run", json=EXAMPLE)
    assert response.status_code == 200
    assert response.json()["rows"] is not None


def test_question_text():
    response = client.post("/api/query/run", json=EXAMPLE)
    assert "נשים" in response.json()["question"]


def test_api_matches_query_builder():
    sql, params = build_query(EXAMPLE)
    expected = [row[1] for row in db.execute(sql, params)]
    response = client.post("/api/query/run", json=EXAMPLE)
    assert [row["value"] for row in response.json()["rows"]] == expected


def test_invalid_measure_returns_no_rows():
    response = client.post("/api/query/run", json={"measure": "median", "groupBy": "year"})
    assert response.status_code == 200
    assert response.json()["rows"] == []


# --- באג 1: בדיקות מונעות (SQL ולוגיקה, לא תלויות בנתונים) ---

def test_average_measure_does_not_use_coalesce():
    """AVG לא צריך לכלול COALESCE — NULL אמור להיספר כ-NULL, לא כ-0."""
    assert "COALESCE" not in MEASURES["average"]


def test_age_to_filter_generates_inclusive_sql():
    """ageTo צריך לייצר age <= ?, לא age < ?."""
    sql, _ = build_query({"measure": "count", "filters": {"ageTo": 30}, "groupBy": "year"})
    assert "age <= ?" in sql
    assert "age < ?" not in sql


def test_free_text_average_ignores_none_values():
    """ממוצע של [10000, None] צריך להיות 10000, לא 5000."""
    from collections import defaultdict
    from app.free_text import answer
    import unittest.mock as mock

    fake_q = {
        "measure": "average",
        "filters": {"city": "תל אביב"},
        "groupBy": "year",
    }
    fake_rows = [(2021, 10000.0), (2021, None)]
    with mock.patch("app.free_text.parser") as mock_parser, \
         mock.patch("app.free_text.db.execute", return_value=fake_rows):
        mock_parser.parse.return_value = fake_q
        result = answer("anything")

    assert result["rows"][0]["value"] == 10000.0


# --- באג 1: שכר ממוצע שגוי ---

QUERY_WOMEN_JLM_25_35 = {
    "measure": "average",
    "filters": {"gender": "F", "city": "ירושלים", "ageFrom": 25, "ageTo": 35,
                "yearFrom": 2021, "yearTo": 2021},
    "groupBy": "year",
}
EXPECTED_AVG_2021 = 11063  # ממוצע ידני מקובץ הנתונים, רק מועסקות


def test_average_excludes_null_income_via_api():
    """AVG צריך להתעלם מ-NULL, לא לטפל בהם כ-0."""
    response = client.post("/api/query/run", json=QUERY_WOMEN_JLM_25_35)
    rows = response.json()["rows"]
    value_2021 = next(r["value"] for r in rows if r["group"] == "2021")
    assert round(value_2021) == EXPECTED_AVG_2021


def test_age_to_is_inclusive_via_api():
    """ageTo=35 צריך לכלול גיל 35 (age <= 35, לא age < 35)."""
    with_35 = client.post("/api/query/run", json=QUERY_WOMEN_JLM_25_35).json()["rows"]
    without_35 = client.post("/api/query/run", json={
        **QUERY_WOMEN_JLM_25_35,
        "filters": {**QUERY_WOMEN_JLM_25_35["filters"], "ageTo": 34},
    }).json()["rows"]
    val_with = next(r["value"] for r in with_35 if r["group"] == "2021")
    val_without = next(r["value"] for r in without_35 if r["group"] == "2021")
    assert val_with != val_without  # גיל 35 משפיע על התוצאה


def test_saved_query_1_returns_correct_average():
    """השאילתה השמורה id=1 צריכה להחזיר 11063 לשנת 2021."""
    response = client.post("/api/saved/1/run")
    rows = response.json()["rows"]
    value_2021 = next(r["value"] for r in rows if r["group"] == "2021")
    assert round(value_2021) == EXPECTED_AVG_2021


def test_free_text_average_excludes_null_income():
    """חישוב ממוצע ב-free_text צריך להתעלם מ-NULL, לא לטפל בהם כ-0."""
    response = client.post(
        "/api/ask",
        json={"text": "מה השכר הממוצע של נשים בירושלים בגילאי 25-35 בשנים 2021-2021 לפי שנה"},
    )
    rows = response.json()["rows"]
    value_2021 = next(r["value"] for r in rows if r["group"] == "2021")
    assert round(value_2021) == EXPECTED_AVG_2021


def test_ask_free_text():
    response = client.post(
        "/api/ask",
        json={"text": "מה השכר הממוצע של נשים בירושלים בשנים 2021-2024 לפי שנה"},
    )
    assert response.status_code == 200
    assert len(response.json()["rows"]) == 4


def test_saved_queries_are_listed_and_run(tmp_path, monkeypatch):
    store = tmp_path / "saved.json"
    store.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(saved_queries, "STORE", store)
    created = client.post("/api/saved", json={"name": "test", "owner": "me", "query": EXAMPLE}).json()
    assert created["id"] in [r["id"] for r in client.get("/api/saved").json()]
    response = client.post(f"/api/saved/{created['id']}/run")
    assert response.status_code == 200
    assert len(response.json()["rows"]) > 0

