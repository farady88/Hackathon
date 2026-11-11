from fastapi.testclient import TestClient

from Fast_API.main import app

client = TestClient(app)


def test_records_returns_loaded_cases():
    r = client.get("/records")
    assert r.status_code == 200
    assert r.json() and "case_id" in r.json()[0]


def test_ask_is_a_stub_for_now():
    # Flip to 200 once run_agent is implemented
    assert client.post("/ask", json={"question": "ERP consolidation?"}).status_code == 501


def test_ask_rejects_empty_or_missing_question():
    assert client.post("/ask", json={"question": ""}).status_code == 422
    assert client.post("/ask", json={}).status_code == 422


def test_embed_is_a_stub_for_now():
    assert client.post("/embed").status_code == 501
