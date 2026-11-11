"""Lynceus hackathon live round: evaluation WITHOUT answers or tuning.

Run locally in approved hackathon environment after indexing all 39 cases.
Stores local reports only (already Git-ignored in project). Does not call Claude.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import lynceus as base
import voyage_hybrid as vh

ROOT = Path(__file__).resolve().parent

def load_questions(path: Path) -> list[dict]:
    items = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(items, list) or len(items) != 5:
        raise ValueError("Expected exactly five live-round questions")
    seen=set()
    for item in items:
        if not isinstance(item,dict) or not isinstance(item.get("id"),str) or not isinstance(item.get("question"),str) or not item["question"].strip():
            raise ValueError("Invalid id/question structure")
        if item["id"] in seen:
            raise ValueError("Question IDs must be unique")
        if "expected_case_ids" in item or "answer" in item:
            raise ValueError("Held-back answers must NOT be supplied to this evaluation")
        seen.add(item["id"])
    return items

def generate(items: list[dict], model: str, mode: str, min_cosine: float, key: str) -> tuple[dict,str]:
    questions=[x['question'] for x in items]
    vectors=vh.cached_query_vectors(questions,model=model,key=key)
    results=[]
    lines=["# Lynceus live-round evidence (human review required)", "",
           "**Status:** Machine-generated candidate rankings only. Human reviewers must verify each result and every source claim before judging or client use.",
           "",f"**Retrieval:** {mode} | model: {model} | minimum cosine: {min_cosine}",
           f"**Case files found:** {len(base.files())}", "", "**No held-back answer labels were used or inferred.**", ""]
    for item in items:
        q=item['question']
        result=vh.rank(q,model=model,key=key,mode=mode,min_cosine=min_cosine,query_vector=vectors[q])
        results.append({'id':item['id'],'question':q,'retrieval':result,'human_checked':False,'human_verdict':None,'failure_reason':None})
        lines.extend([f"## {item['id']}","",f"**Client question:** {q}","",
                      f"**Search outcome:** {'No strong match identified' if result['no_strong_match'] else str(len(result['results']))+' candidate(s)'}", ""])
        for i,c in enumerate(result['results'],1):
            lines.extend([f"### Candidate {i}: {c['case_id']}","",
                          f"- Cosine similarity: {c['cosine_similarity']} (not a confidence probability)",
                          f"- Vector rank: {c['vector_rank']}; lexical rank: {c['lexical_rank']}",
                          f"- Match explanation: {c['reason']}",
                          f"- Local original source: `corpus/{c['case_id']}.txt`", ""])
            for s in c.get('summary',[]):
                evidence=s.get('evidence',[])
                ranges=', '.join(str(e.get('line_start'))+'-'+str(e.get('line_end')) for e in evidence)
                lines.extend([f"- Original excerpt (source lines {ranges}): {s.get('text','')}",""])
        if not result['results']:
            candidates=', '.join(f"{x['case_id']} ({x['similarity']})" for x in result.get('top_vector_candidates',[]))
            lines.extend(["**Diagnostic only — top raw vector neighbours:** "+candidates,""])
        lines.extend(["**Human verdict:** NOT REVIEWED", "",
                      "**Which source lines support relevance / outcomes?** [reviewer to fill]", "",
                      "**Is the answer useful and accurate?** [reviewer to fill]", "",
                      "**If missed:** [enrichment / matching / question / corpus; explain after review]", "",
                      "**Confidentiality check:** [reviewer to fill before presenting]", ""])
    report={"created_at":datetime.now(timezone.utc).isoformat(),"model":model,"mode":mode,
            "min_cosine":min_cosine,"case_count":len(base.files()),"questions_count":len(items),
            "integrity":"No expected case IDs or judge answers provided; no tuning performed.","cases":results}
    return report, '\n'.join(lines)+'\n'

def main(argv=None):
    ap=argparse.ArgumentParser(description="Lynceus: five unlabelled live-round queries, batched and recorded")
    ap.add_argument('--questions',type=Path,default=ROOT/'live_round_questions.json')
    ap.add_argument('--mode',choices=('semantic','hybrid'),default='hybrid')
    ap.add_argument('--model',default=vh.MODEL)
    ap.add_argument('--min-cosine',type=float,default=0.40)
    ap.add_argument('--approved-external-processing',action='store_true')
    opts=ap.parse_args(argv)
    if not opts.approved_external_processing:
        ap.error('Requires --approved-external-processing after hackathon authorisation for Voyage')
    try:
        questions=load_questions(opts.questions)
        key=vh.require_authorisation(opts.approved_external_processing)
        idx=vh.checked_index(opts.model)
        if len(idx)!=39:
            raise RuntimeError(f'Expected 39 indexed cases for live round; found {len(idx)}. Verify import and indexing first.')
        result,md=generate(questions,opts.model,opts.mode,opts.min_cosine,key)
        reports=ROOT/'reports'
        reports.mkdir(parents=True,exist_ok=True)
        base.json_write(reports/'live_round_results.json',result)
        (reports/'live_round_evidence.md').write_text(md,encoding='utf-8')
        print('Indexed cases:',result['case_count'])
        for item in result['cases']:
            matches=item['retrieval']['results']
            print(f"{item['id']}: "+(', '.join(f"{r['case_id']} ({r['cosine_similarity']:.3f})" for r in matches) or 'NO STRONG MATCH'))
        print('Saved local reports/live_round_results.json and reports/live_round_evidence.md (HUMAN REVIEW PENDING).')
    except (ValueError,RuntimeError,FileNotFoundError,OSError) as exc:
        print('Error:',exc,file=sys.stderr)
        return 1
    return 0

if __name__=='__main__':
    raise SystemExit(main())
