import requests
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from Fast_API.main import app

api = TestClient(app)


def run_ui(monkeypatch):
    # Route the UI's HTTP calls straight into the FastAPI app, no server needed
    monkeypatch.setattr(requests, "request", lambda method, url, timeout=None, **kw: api.request(
        method, url.split(":8000")[1], **kw))
    return AppTest.from_file("../Streamlit_UI/app.py").run()


def test_case_lookup_shows_record(monkeypatch):
    at = run_ui(monkeypatch)
    at.text_input[1].set_value("case-142")
    at.button[1].click().run()
    assert not at.exception and not at.error
    assert "case-142" in at.json[0].value


def test_unknown_case_shows_error(monkeypatch):
    at = run_ui(monkeypatch)
    at.text_input[1].set_value("case-nope")
    at.button[1].click().run()
    assert "404" in at.error[0].value


def test_ask_shows_answer_and_sources(monkeypatch):
    monkeypatch.setattr("Fast_API.main.run_agent", lambda question: {
        "answer": "See case-142.", "sources": [{"id": "case-142", "score": 0.4}]})
    at = run_ui(monkeypatch)
    at.text_input[0].set_value("ERP consolidation?")
    at.button[0].click().run()
    assert not at.exception and not at.error
    assert any("See case-142." in m.value for m in at.markdown)
    assert len(at.dataframe) == 1
