"""Synthetic tests only; NOT proof of real-corpus Recall@3."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import lynceus as l


class TestLynceus(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.base=Path(self.t.name)
        for d in ('corpus','enriched/drafts','enriched/reviewed','reports'):
            (self.base/d).mkdir(parents=True,exist_ok=True)
        (self.base/'corpus'/'101.txt').write_text('A team rewrote thousands of validation rules.\nThe automated rules migration reduced manual rework.\n',encoding='utf-8')
        (self.base/'corpus'/'102.txt').write_text('Satellite sensors detect methane leaks in gas pipelines.\nAlerts reduced detection time for gas leaks.\n',encoding='utf-8')
        self.p=patch.object(l,'ROOT',self.base)
        self.p.start()
    def tearDown(self):
        self.p.stop()
        self.t.cleanup()
    def test_source_has_true_line_numbers(self):
        result=l.top_source_sentences('101','rewrite old validation rules')
        lines=l.source('101').splitlines()
        self.assertTrue(result)
        for item in result:
            self.assertEqual(len(item['lines']),2)
            a,b=item['lines']
            self.assertTrue(1<=a<=b<=len(lines))
            self.assertIn(item['text'], ' '.join(lines[a-1:b]))
    def test_retrieves_cross_sector_concept(self):
        r=l.search('A bank must rewrite legacy validation rules')
        self.assertFalse(r['no_strong_match'],r)
        self.assertEqual(r['results'][0]['case_id'],'101')
    def test_retrieves_leak(self):
        r=l.search('A water company wants to detect methane pipeline leaks')
        self.assertEqual(r['results'][0]['case_id'],'102')
    def test_abstains_on_unrelated_query(self):
        r=l.search('quantum teleportation to Mars for starships')
        self.assertTrue(r['no_strong_match'],r)
    def test_rejects_fabricated_quote(self):
        with self.assertRaises(ValueError):
            l.verify_evidence('101',[{'line_start':1,'line_end':1,'quote':'A fictional 9000 percent improvement'}])
    def test_accepts_real_quote(self):
        l.verify_evidence('101',[{'line_start':1,'line_end':1,'quote':'rewrote thousands of validation rules'}])
    def test_rejects_unsafe_case_id(self):
        with self.assertRaises(ValueError):
            l.case_path('../private')
    def test_non_reviewed_agent_output_not_used(self):
        draft=l.base_record('101')
        draft['problem']={'text':'completely secret moon agriculture','evidence':[]}
        l.json_write(self.base/'enriched'/'drafts'/'101.json',draft)
        r=l.search('moon agriculture subsidies')
        self.assertTrue(r['no_strong_match'])
    def test_reviewed_field_increases_search(self):
        record=l.base_record('101')
        record['problem']={'text':'Legacy banking policy transformation', 'evidence':[{'line_start':1,'line_end':1,'quote':'rewrote thousands of validation rules'}]}
        record['_reviewer']='Synthetic Unit Tester'
        record['_reviewed_at']='2026-11-11T00:00:00+00:00'
        record['_source_sha256']=l.fp(l.source('101'))
        l.json_write(self.base/'enriched'/'reviewed'/'101.json',record)
        r=l.search('banking policy transformation')
        self.assertEqual(r['results'][0]['case_id'],'101')
        self.assertTrue(r['results'][0]['reviewed'])
    def test_unapproved_record_never_read(self):
        record=l.base_record('101')
        record['problem']={'text':'banking advice', 'evidence':[{'line_start':1,'line_end':1,'quote':'rewrote thousands of validation rules'}]}
        l.json_write(self.base/'enriched'/'reviewed'/'101.json',record)
        self.assertIsNone(l.reviewed_record('101'))

    def test_review_invalidated_when_source_changes(self):
        record=l.base_record('101')
        record['_reviewer']='Synthetic Unit Tester'
        record['_reviewed_at']='2026-11-11T00:00:00+00:00'
        record['_source_sha256']=l.fp(l.source('101'))
        l.json_write(self.base/'enriched'/'reviewed'/'101.json',record)
        self.assertIsNotNone(l.reviewed_record('101'))
        (self.base/'corpus'/'101.txt').write_text('The source has changed and needs fresh review.\n',encoding='utf-8')
        self.assertIsNone(l.reviewed_record('101'))

    def test_invalid_review_never_read(self):
        record=l.base_record('101')
        record['problem']={'text':'invented technique','evidence':[{'line_start':1,'line_end':1,'quote':'fake magic invented here'}]}
        l.json_write(self.base/'enriched'/'reviewed'/'101.json',record)
        self.assertIsNone(l.reviewed_record('101'))

if __name__=='__main__':unittest.main()
