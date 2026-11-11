"""Synthetic tests with a scripted fake model; NOT proof of real-corpus Recall@3."""
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import agent
import grounding
from knowledge_store import CorpusStore

GOOD = {"no_match": False, "results": [{
    "case_id": "101", "why_matched": "Same rule-rewriting problem, described by another sector.",
    "summary": [
        {"text": "The team rewrote more than 2,000 validation rules with generative AI.",
         "evidence": [{"line_start": 1, "line_end": 1, "quote": "rewrote more than 2,000 validation rules"}]},
        {"text": "Each rule took about a minute.",
         "evidence": [{"line_start": 2, "line_end": 2, "quote": "Each rule took about a minute"}]}]}]}
NO_MATCH = {"no_match": True, "results": []}
SEARCH = ("search_cases", {"query": "rewrite legacy rules"})


def variant(sentence=0, **changes):
    answer = deepcopy(GOOD)
    target = answer["results"][0]["summary"][sentence]
    for key, value in changes.items():
        if key == "quote":
            target["evidence"][0]["quote"] = value
        else:
            target[key] = value
    return answer


class FakeClient:
    """Replays scripted tool calls; the last one repeats if the agent keeps asking."""
    def __init__(self, *steps):
        self.steps, self.calls = list(steps), 0
        self.messages = SimpleNamespace(create=self.create)

    def create(self, **kwargs):
        name, args = self.steps[min(self.calls, len(self.steps) - 1)]
        self.calls += 1
        block = SimpleNamespace(type="tool_use", id=f"t{self.calls}", name=name, input=args)
        return SimpleNamespace(content=[block], stop_reason="tool_use")


class TestAgent(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.base = Path(self.t.name)
        (self.base / "101.txt").write_text(
            "A team rewrote more than 2,000 validation rules with generative AI.\nEach rule took about a minute.\n",
            encoding="utf-8")
        (self.base / "102.txt").write_text("Satellite sensors detect methane leaks in gas pipelines.\n", encoding="utf-8")
        self.store = CorpusStore([self.base])
        self.p = patch.object(agent, "LOG_PATH", self.base / "logs" / "agent_log.jsonl")
        self.p.start()

    def tearDown(self):
        self.p.stop()
        self.t.cleanup()

    def run_steps(self, *steps):
        client = FakeClient(*steps)
        return agent.run_agent("A bank must rewrite legacy rules", self.store, client), client

    def test_grounded_answer_is_returned_and_logged(self):
        out, _ = self.run_steps(SEARCH, ("submit_answer", GOOD))
        self.assertFalse(out["no_strong_match"], out)
        self.assertEqual(out["results"][0]["case_id"], "101")
        self.assertIn("not human-reviewed", out["results"][0]["summary_type"])
        self.assertIn("agent_search", agent.LOG_PATH.read_text(encoding="utf-8"))

    def test_no_match_gives_the_refusal_sentence(self):
        out, _ = self.run_steps(SEARCH, ("submit_answer", NO_MATCH))
        self.assertTrue(out["no_strong_match"])
        self.assertEqual(out["reason"], grounding.REFUSAL_SENTENCE)

    def test_fabricated_quote_gets_one_repair_turn(self):
        bad = variant(quote="a fictional 9000 percent improvement")
        out, client = self.run_steps(SEARCH, ("submit_answer", bad), ("submit_answer", GOOD))
        self.assertEqual(client.calls, 3)
        self.assertEqual(out["results"][0]["case_id"], "101")

    def test_fabricated_quote_twice_drops_the_result(self):
        bad = variant(quote="a fictional 9000 percent improvement")
        out, _ = self.run_steps(SEARCH, ("submit_answer", bad))
        self.assertTrue(out["no_strong_match"])
        self.assertEqual(out["dropped_ungrounded"], ["101"])
        self.assertNotEqual(out["reason"], grounding.REFUSAL_SENTENCE)

    def test_invented_figure_falls_back_to_verbatim_quotes(self):
        bad = variant(text="The team rewrote 9,000 validation rules.")
        out, _ = self.run_steps(SEARCH, ("submit_answer", bad))
        result = out["results"][0]
        self.assertEqual(result["summary_type"], "verbatim source excerpts")
        self.assertEqual(result["summary"][0]["text"], "rewrote more than 2,000 validation rules")

    def test_case_never_retrieved_cannot_be_cited(self):
        out, _ = self.run_steps(("submit_answer", GOOD))
        self.assertEqual(out["dropped_ungrounded"], ["101"])

    def test_three_sentence_summary_is_invalid(self):
        bad = deepcopy(GOOD)
        bad["results"][0]["summary"].append(bad["results"][0]["summary"][0])
        out, _ = self.run_steps(SEARCH, ("submit_answer", bad))
        self.assertTrue(out["no_strong_match"])
        self.assertIn("valid answer", out["reason"])

    def test_loop_stops_at_turn_cap(self):
        out, client = self.run_steps(("read_case", {"case_id": "102"}))
        self.assertEqual(client.calls, agent.MAX_TURNS)
        self.assertTrue(out["no_strong_match"])

    def test_uncited_sentence_is_flagged(self):
        result = deepcopy(GOOD["results"][0])
        result["summary"][1]["evidence"] = []
        self.assertEqual(grounding.find_uncited(result), ["sentence 2 has no citation"])

    def test_figures_match_across_number_formats(self):
        result = {"summary": [{"text": "It serves 100,000 employees in 150 countries.",
                               "evidence": [{"quote": "lebih dari 100.000 karyawan di 150 negara"}]}]}
        self.assertEqual(grounding.find_unsupported_figures(result), [])

    def test_new_case_file_is_picked_up_and_sidecars_skipped(self):
        (self.base / "103.txt").write_text("A new live-round case.\n", encoding="utf-8")
        (self.base / "._103.txt").write_text("macOS sidecar", encoding="utf-8")
        self.assertEqual(sorted(self.store.paths()), ["101", "102", "103"])


if __name__ == "__main__":
    unittest.main()
