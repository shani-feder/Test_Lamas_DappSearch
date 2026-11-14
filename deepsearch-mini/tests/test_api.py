from fastapi.testclient import TestClient

from app import db, saved_queries
from app.free_text import answer
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

def test_age_to_filter_generates_inclusive_sql():
    """ageTo צריך לייצר age <= ?, לא age < ?."""
    sql, _ = build_query({"measure": "count", "filters": {"ageTo": 30}, "groupBy": "year"})
    assert "age <= ?" in sql
    assert "age < ?" not in sql


def test_free_text_average_ignores_none_values():
    """ממוצע של רשומות עם NULL צריך להתעלם מהן, לא לספור כ-0."""
    import unittest.mock as mock

    fake_q = {"measure": "average", "filters": {"city": "תל אביב"}, "groupBy": "year"}
    # 11 רשומות: 10 עם שכר כדי לעבור את סף החיסיון, אחת NULL
    # כעת build_query מחזיר 3 עמודות: (group, value, count)
    fake_rows = [(2021, 10000.0, 10)] * 10 + [(2021, None, 10)]
    with mock.patch("app.free_text.parser") as mock_parser, \
         mock.patch("app.query_runner.db.execute", return_value=fake_rows):
        mock_parser.parse.return_value = fake_q
        result = answer("anything")

    assert result["rows"][0]["value"] == 10000.0


# --- באג 2: בדיקות מונעות ---

def test_suppression_hides_value_below_threshold():
    """קבוצה עם פחות מ-10 רשומות צריכה להיות מוסתרת ב-average."""
    from app.query_builder import suppress_rows
    rows = [{"group": "2023", "value": 10000.0, "count": 9}]
    result = suppress_rows(rows, "average")
    assert result == [{"group": "2023", "value": None, "suppressed": True}]


def test_suppression_shows_value_at_threshold():
    """קבוצה עם בדיוק 10 רשומות צריכה להיות גלויה ב-average."""
    from app.query_builder import suppress_rows
    rows = [{"group": "2023", "value": 10000.0, "count": 10}]
    result = suppress_rows(rows, "average")
    assert result == [{"group": "2023", "value": 10000.0}]


def test_suppression_count_threshold_is_5():
    """סף החיסיון ל-count הוא 5 רשומות."""
    from app.query_builder import suppress_rows
    assert suppress_rows([{"group": "x", "value": 4, "count": 4}], "count") == [{"group": "x", "value": None, "suppressed": True}]
    assert suppress_rows([{"group": "x", "value": 5, "count": 5}], "count") == [{"group": "x", "value": 5}]


def test_suppression_applied_via_api():
    """נשים באילת 2023 צריכות להיות מוסתרות כי יש פחות מ-10 רשומות."""
    response = client.post("/api/query/run", json={
        "measure": "average",
        "filters": {"gender": "F", "city": "אילת"},
        "groupBy": "year",
    })
    rows = {r["group"]: r for r in response.json()["rows"]}
    assert rows["2023"]["value"] is None
    assert rows["2023"]["suppressed"] is True


def test_suppression_does_not_hide_other_groups():
    """קבוצות עם מספיק רשומות מוחזרות כרגיל גם כשיש קבוצות מוסתרות."""
    response = client.post("/api/query/run", json={
        "measure": "count",
        "filters": {"gender": "F", "city": "אילת"},
        "groupBy": "year",
    })
    rows = {r["group"]: r for r in response.json()["rows"]}
    assert rows["2021"]["value"] is not None  # 7 רשומות, עובר סף 5
    assert rows["2023"]["value"] is None      # 3 רשומות, לא עובר


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


def test_saved_query_4_returns_correct_average():
    """השאילתה השמורה id=4 צריכה להחזיר 11411 לשנת 2021."""
    response = client.post("/api/saved/4/run")
    rows = response.json()["rows"]
    value_2021 = next(r["value"] for r in rows if r["group"] == "2021")
    assert round(value_2021) == 11411


def test_all_execution_paths_return_same_rows(tmp_path, monkeypatch):
    """כל מסלול שמשתמש ב-execute_query מחזיר אותן תוצאות."""
    import unittest.mock as mock
    from app.query_runner import execute_query

    store = tmp_path / "saved.json"
    store.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(saved_queries, "STORE", store)

    expected = execute_query(EXAMPLE)

    direct = client.post("/api/query/run", json=EXAMPLE).json()["rows"]

    saved_id = client.post("/api/saved", json={"name": "t", "owner": "u", "query": EXAMPLE}).json()["id"]
    saved = client.post(f"/api/saved/{saved_id}/run").json()["rows"]

    with mock.patch("app.free_text.parser") as mock_parser:
        mock_parser.parse.return_value = EXAMPLE
        free = client.post("/api/ask", json={"text": "anything"}).json()["rows"]

    assert direct == saved == free == expected


def test_saved_queries_are_listed_and_run(tmp_path, monkeypatch):
    store = tmp_path / "saved.json"
    store.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(saved_queries, "STORE", store)
    created = client.post("/api/saved", json={"name": "test", "owner": "me", "query": EXAMPLE}).json()
    assert created["id"] in [r["id"] for r in client.get("/api/saved").json()]
    response = client.post(f"/api/saved/{created['id']}/run")
    assert response.status_code == 200
    assert len(response.json()["rows"]) > 0

