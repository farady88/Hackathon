"""Offline, synthetic Voyage tests: never contact an external provider."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import lynceus as base
import voyage_hybrid as vh

class TestVoyageHybrid(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        for d in ('corpus','enriched/vectors','enriched/reviewed','reports'):
            (self.root/d).mkdir(parents=True,exist_ok=True)
        (self.root/'corpus'/'case-101.txt').write_text('The insurance claims process is slow. Staff automate claims processing.', encoding='utf-8')
        (self.root/'corpus'/'case-102.txt').write_text('Industrial sensors help detect gas leaks in pipelines.', encoding='utf-8')
        self.p1=patch.object(base,'ROOT',self.root)
        self.p2=patch.object(vh,'CACHE_DIR',self.root/'enriched'/'vectors')
        self.p1.start(); self.p2.start()
    def tearDown(self):
        self.p2.stop();self.p1.stop();self.temp.cleanup()

    def fake_api(self,inputs,*,model,input_type,key):
        self.assertEqual(model,'voyage-4')
        self.assertEqual(key,'fake-not-a-key')
        self.assertIn(input_type,('document','query'))
        def vec(text):
            s=text.lower()
            if 'insurance' in s or 'claims' in s or 'sinistres' in s:
                return [1.0,0.0,0.0]
            if 'leak' in s or 'sensors' in s or 'gaz' in s:
                return [0.0,1.0,0.0]
            return [0.0,0.0,1.0]
        return [vec(t) for t in inputs]

    def test_approval_required_even_if_key_present(self):
        with patch.dict('os.environ',{'VOYAGE_API_KEY':'fake-not-a-key'}):
            with self.assertRaisesRegex(RuntimeError,'organiser approves'):
                vh.require_authorisation(False)
            self.assertEqual(vh.require_authorisation(True),'fake-not-a-key')

    def test_index_caches_and_incremental_new_cases(self):
        with patch.object(vh,'embeddings',side_effect=self.fake_api) as api:
            self.assertEqual(vh.build_index(model='voyage-4',key='fake-not-a-key'),(2,2))
            self.assertEqual(vh.build_index(model='voyage-4',key='fake-not-a-key'),(0,2))
            (self.root/'corpus'/'case-103.txt').write_text('More insurance claims to manage.',encoding='utf-8')
            self.assertEqual(vh.build_index(model='voyage-4',key='fake-not-a-key'),(1,3))
            self.assertEqual(api.call_count,2)

    def test_changed_case_invalidates_index(self):
        with patch.object(vh,'embeddings',side_effect=self.fake_api):
            vh.build_index(model='voyage-4',key='fake-not-a-key')
            (self.root/'corpus'/'case-101.txt').write_text('Changed source data about banking systems',encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError,'out of date'):
                vh.checked_index('voyage-4')
            self.assertEqual(vh.build_index(model='voyage-4',key='fake-not-a-key'),(1,2))

    def test_semantic_cross_language(self):
        with patch.object(vh,'embeddings',side_effect=self.fake_api):
            vh.build_index(model='voyage-4',key='fake-not-a-key')
            r=vh.rank('Automatisation des sinistres',model='voyage-4',key='fake-not-a-key',mode='semantic')
            self.assertEqual(r['results'][0]['case_id'],'case-101')
            self.assertEqual(r['results'][0]['summary_type'],'verbatim source excerpts')
            self.assertEqual(r['results'][0]['summary'][0]['evidence'][0]['line_start'],1)

    def test_hybrid_supports_search(self):
        with patch.object(vh,'embeddings',side_effect=self.fake_api):
            vh.build_index(model='voyage-4',key='fake-not-a-key')
            r=vh.rank('A utility wants gas pipeline leak detection',model='voyage-4',key='fake-not-a-key',mode='hybrid')
            self.assertEqual(r['results'][0]['case_id'],'case-102')

    def test_no_match_abstains(self):
        with patch.object(vh,'embeddings',side_effect=self.fake_api):
            vh.build_index(model='voyage-4',key='fake-not-a-key')
            r=vh.rank('Quantum teleportation to another planet',model='voyage-4',key='fake-not-a-key',mode='hybrid')
            self.assertTrue(r['no_strong_match'])

    def test_offline_evaluation_counts(self):
        data=[{'id':'t1','question':'Insurance claims','expected_case_ids':['case-101']},
              {'id':'t2','question':'Teleportation','expected_case_ids':[],'expect_no_match':True}]
        f=self.root/'tests.json';f.write_text(json.dumps(data),encoding='utf-8')
        with patch.object(vh,'embeddings',side_effect=self.fake_api):
            vh.build_index(model='voyage-4',key='fake-not-a-key')
            r=vh.evaluate(test_set=f,model='voyage-4',key='fake-not-a-key',mode='semantic',min_cosine=.5)
            self.assertEqual(r['recall_at_3'],1.0)
            self.assertEqual(r['no_match_accuracy'],1.0)
            self.assertEqual(r['counts']['positive'],1)

    def test_cosine_dimension_validation(self):
        self.assertAlmostEqual(vh.cosine([1,0],[1,0]),1)
        with self.assertRaises(ValueError):
            vh.cosine([1],[1,0])


    def test_batch_evaluation_reuses_queries_across_modes(self):
        data=[{'id':'t1','question':'Insurance claims','expected_case_ids':['case-101']},
              {'id':'t2','question':'Gas pipeline leaks','expected_case_ids':['case-102']},
              {'id':'t3','question':'Teleportation','expected_case_ids':[], 'expect_no_match':True}]
        f=self.root/'tests.json';f.write_text(json.dumps(data),encoding='utf-8')
        with patch.object(vh,'embeddings',side_effect=self.fake_api) as api:
            vh.build_index(model='voyage-4',key='fake-not-a-key')
            doc_calls=api.call_count
            a=vh.evaluate(test_set=f,model='voyage-4',key='fake-not-a-key',mode='semantic',min_cosine=.5)
            self.assertEqual(api.call_count,doc_calls+1)
            self.assertEqual(len(api.call_args.args[0]),3)
            b=vh.evaluate(test_set=f,model='voyage-4',key='fake-not-a-key',mode='hybrid',min_cosine=.5)
            self.assertEqual(api.call_count,doc_calls+1)  # No further HTTP calls
            self.assertEqual(a['counts']['positive'],2)
            self.assertEqual(b['counts']['positive'],2)
            query_cache=(self.root/'enriched/vectors/voyage-4-query-vectors.json').read_text()
            self.assertNotIn('Insurance claims',query_cache)
            self.assertNotIn('fake-not-a-key',query_cache)

    def test_changed_question_embeds_only_new_query(self):
        with patch.object(vh,'embeddings',side_effect=self.fake_api) as api:
            vh.build_index(model='voyage-4',key='fake-not-a-key')
            vh.cached_query_vectors(['Insurance claims','Gas leaks'],model='voyage-4',key='fake-not-a-key')
            self.assertEqual(api.call_count,2)
            v=vh.cached_query_vectors(['Gas leaks','Insurance claims','New claims question'],model='voyage-4',key='fake-not-a-key')
            self.assertEqual(api.call_count,3)
            self.assertEqual(api.call_args.args[0],['New claims question'])
            self.assertEqual(len(v),3)

    def test_cached_query_vectors_require_existing_index(self):
        with self.assertRaisesRegex(RuntimeError,'No vector index'):
            vh.cached_query_vectors(['Insurance claims'],model='voyage-4',key='fake-not-a-key')

if __name__=='__main__': unittest.main()
