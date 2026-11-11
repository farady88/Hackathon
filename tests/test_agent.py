"""Agent tests with a fake Claude client: no network, no API cost."""
from types import SimpleNamespace

from Fast_API import agent

QUESTION = "Have we moved business software to the cloud on AWS?"


class FakeClient:
    def __init__(self, stop_reason="end_turn"):
        self.requests = []
        self.stop_reason = stop_reason
        self.messages = SimpleNamespace(create=self.create)

    def create(self, **kwargs):
        self.requests.append(kwargs)
        blocks = [SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text="Canned answer.")]
        return SimpleNamespace(content=blocks, stop_reason=self.stop_reason)


def test_top_3_search_hits_are_sent_to_haiku():
    fake = FakeClient()
    result = agent.run_agent(QUESTION, client=fake)

    assert result["answer"] == "Canned answer."
    assert 1 <= len(result["sources"]) <= 3
    request = fake.requests[0]
    assert request["model"] == "claude-haiku-5-5"
    prompt = request["messages"][0]["content"]
    assert QUESTION in prompt
    for hit in result["sources"]:
        assert f'<case id="{hit["id"]}">' in prompt


def test_no_search_hit_skips_the_model():
    fake = FakeClient()
    result = agent.run_agent("zzzz qqqq xxxx", client=fake)
    assert result == {"answer": agent.NO_MATCH, "sources": []}
    assert fake.requests == []


def test_refusal_is_reported():
    result = agent.run_agent(QUESTION, client=FakeClient(stop_reason="refusal"))
    assert "declined" in result["answer"]
