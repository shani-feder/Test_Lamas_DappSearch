from fastapi.testclient import TestClient

from app import db, saved_queries
from app.main import app
from app.query_builder import build_query

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


def test_ask_free_text():
    response = client.post(
        "/api/ask",
        json={"text": "מה השכר הממוצע של נשים בירושלים בשנים 2021-2024 לפי שנה"},
    )
    assert response.status_code == 200
    assert len(response.json()["rows"]) == 4


def test_saved_queries_are_listed_and_run():
    saved = client.get("/api/saved").json()
    assert len(saved) >= 4
    response = client.post(f"/api/saved/{saved[0]['id']}/run")
    assert response.status_code == 200
    assert len(response.json()["rows"]) == 4


def test_save_query(tmp_path, monkeypatch):
    store = tmp_path / "saved.json"
    store.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(saved_queries, "STORE", store)
    created = client.post("/api/saved", json={"name": "test", "owner": "me", "query": EXAMPLE}).json()
    assert created["id"] == 1
    assert client.post("/api/saved/1/run").status_code == 200
