"""Offline tests for the search UI. No APIs, no source corpus needed."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import voyage_search_app as app
import lynceus as base


class TestSearchWeb(unittest.TestCase):
    def test_result_escapes_html_and_links_to_source(self):
        sample = {"no_strong_match":False, "results":[{"case_id":"case-123", "cosine_similarity":0.75,
            "reason":"<script>alert(1)</script>","summary_type":"verbatim source excerpts",
            "summary":[{"text":"<secret> & evidence", "evidence":[{"line_start":1,"line_end":1}]}]}]}
        html = app.result_view('insurance <script>', sample, mode='hybrid', min_cosine=.4, count=39)
        self.assertIn('&lt;script&gt;',html)
        self.assertNotIn('<script>',html)
        self.assertIn('&lt;secret&gt; &amp; evidence',html)
        self.assertIn('/source/case-123',html)
        self.assertIn('L1–L1',html)

    def test_reviewed_details_shows_outcome_with_source_link(self):
        record = {
            'problem': {'text':'Improve enterprise adoption', 'evidence':[{'line_start':1,'line_end':1,'quote':'full original'}]},
            'scale_outcomes':[{'text':'121 minutes saved weekly per employee', 'evidence':[{'line_start':1,'line_end':1,'quote':'full original'}]}],
            'capabilities':[{'text':'Meeting recap automation','evidence':[{'line_start':1,'line_end':1}]}],
            'reuse':[{'text':'Could support regulated firms', 'evidence':[{'line_start':1,'line_end':1}]}],
            'disclosure_status':'unknown'}
        with patch.object(base, 'reviewed_record', return_value=record):
            html=app.reviewed_details('case-228')
        self.assertIn('121 minutes saved weekly', html)
        self.assertIn('Potential reuse — proposals, not proven outcomes', html)
        self.assertIn('/source/case-228#L1', html)
        self.assertIn('not confirmed for client-facing use',html)

    def test_unreviewed_case_no_ai_facts(self):
        with patch.object(base, 'reviewed_record', return_value=None):
            html=app.reviewed_details('case-999')
        self.assertIn('Not reviewed',html)
        self.assertNotIn('Delivered capabilities',html)

    def test_reviewed_fields_html_escape(self):
        record={'problem':{'text':'<script>alert(1)</script>', 'evidence':[{'line_start':1,'line_end':1}]},
                'scale_outcomes':[], 'disclosure_status':'unknown'}
        with patch.object(base, 'reviewed_record', return_value=record):
            html=app.reviewed_details('case-123')
        self.assertIn('&lt;script&gt;',html)
        self.assertNotIn('<script>',html)

    def test_result_view_uses_reviewed_details_without_changing_rank(self):
        r={'no_strong_match':False,'results':[{'case_id':'case-222','cosine_similarity':.77,
          'summary_type':'verbatim source excerpts','reason':'Vector match','summary':[]}]}
        with patch.object(app, 'reviewed_details', return_value='<div class="review">details</div>') as add:
            html=app.result_view('test query',r,mode='hybrid',min_cosine=.4,count=39)
        add.assert_called_once_with('case-222')
        self.assertIn('details',html)
        self.assertIn('/source/case-222',html)

    def test_no_match_is_not_overclaimed(self):
        html = app.result_view('crew rostering', {'no_strong_match':True,'results':[]}, mode='hybrid',min_cosine=.4,count=39)
        self.assertIn('No strong match found',html)
        self.assertIn('not proof that no such work exists',html)

    def test_home_does_not_claim_review(self):
        html=app.page(app.base_form('', 'hybrid', .4, 39))
        self.assertIn('human review required',html)
        self.assertIn('39',html)

    def test_source_fails_on_path_traversal(self):
        with self.assertRaises((ValueError,FileNotFoundError)):
            app.source_view('../hackathon-secrets')

    def test_status_does_not_require_api_key(self):
        with patch.object(base,'files',return_value=[]), patch.object(app.vh,'checked_index',side_effect=RuntimeError('no cache')):
            self.assertEqual(app.main(['status']),0)

    def test_server_is_local(self):
        with patch.object(app.vh,'require_authorisation',return_value='fake'), \
             patch.object(app.vh,'build_index',return_value=(0,39)), \
             patch.object(app,'ThreadingHTTPServer', side_effect=RuntimeError('stop')) as server:
            self.assertEqual(app.main(['serve','--approved-external-processing']),1)
            self.assertEqual(server.call_args.args[0],('127.0.0.1',8001))

if __name__ == '__main__':
    unittest.main()
