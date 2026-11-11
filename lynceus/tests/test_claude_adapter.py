import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from claude_enrichment_adapter import build_request, parse_message_response, ask_claude

class ClaudeAdapterTests(unittest.TestCase):
    def setUp(self):
        self.payload={"case_id":"case-001", "prompt":"Extract facts and give exact citations", "source_lines":[{"line":1,"text":"A tool reduced wait time by 10 minutes."}]}

    def test_request_has_source_and_prompt(self):
        req=build_request(self.payload)
        self.assertEqual(req["model"],"claude-sonnet-4-6")
        self.assertIn("case-001",req["messages"][0]["content"])
        self.assertIn("source_lines",req["messages"][0]["content"])
        self.assertTrue(req["system"])

    def test_no_case_rejected(self):
        with self.assertRaises(ValueError):build_request({"prompt":"x", "source_lines":[]})

    def test_no_prompt_rejected(self):
        with self.assertRaises(ValueError):build_request({"case_id":"x", "source_lines":[]})

    def test_json_response(self):
        r=parse_message_response({"content":[{"type":"text","text":'{"case_id":"case-001"}'}],"stop_reason":"end_turn"})
        self.assertEqual(r["case_id"],"case-001")

    def test_fenced_json_response(self):
        r=parse_message_response({"content":[{"type":"text","text":"```json\n{\"case_id\":\"case-001\"}\n```"}],"stop_reason":"end_turn"})
        self.assertEqual(r["case_id"],"case-001")

    def test_truncation_rejected(self):
        with self.assertRaises(ValueError):parse_message_response({"content":[{"type":"text","text":'{"case_id":"x"}'}],"stop_reason":"max_tokens"})

    def test_missing_key_rejected_before_network(self):
        with self.assertRaises(RuntimeError):ask_claude(self.payload,"")

    def test_mismatched_case_rejected(self):
        class Fake:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self):return json.dumps({"content":[{"type":"text","text":'{"case_id":"case-002"}'}],"stop_reason":"end_turn"}).encode()
        with patch("claude_enrichment_adapter.request.urlopen", return_value=Fake()):
            with self.assertRaises(ValueError):ask_claude(self.payload,"test-key")

if __name__ == "__main__":unittest.main()
