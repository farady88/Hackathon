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


def test_unknown_case_and_stubbed_ask_show_errors(monkeypatch):
    at = run_ui(monkeypatch)
    at.text_input[1].set_value("case-nope")
    at.button[1].click().run()
    assert "404" in at.error[0].value

    at.text_input[0].set_value("ERP consolidation?")
    at.button[0].click().run()
    # Flip to checking the answer once run_agent is implemented
    assert "501" in at.error[0].value
