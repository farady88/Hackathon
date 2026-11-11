"""Lynceus: local-first, grounded case-study search. Standard library only.

Never transfer private corpus to an unapproved service. This starter has no AI
service dependency. Optional agent integration requires explicit authorization.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
from hashlib import sha256
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from urllib.parse import parse_qs, quote, unquote, urlparse

ROOT = Path(__file__).resolve().parent
STOP = set('a an and are as at be been by can client clients company could cut do does for from get has have help how i in into is it its of on or our past project projects reduce find looking matching with without my need needs new not old to the their them there these they this through using wants want we were what when where which who will work would you your about across years year more less than'.split())
ALIASES = [
    {'call','contact','centre','center','customer','service','support','helpline','citizen','inbound','triage'},
    {'backlog','queue','wait','waiting','delay','bottleneck','response'},
    {'rewrite','rewriting','modernise','modernize','migrate','migration','transform','replace','convert','refactor'},
    {'rules','rule','validation','checks','logic','compliance','policy','policies'},
    {'leak','leaks','leakage','emissions','methane','escape','loss'},
    {'sensors','sensor','satellite','remote','monitoring','detection','detect'},
    {'genai','generative','llm','language','model','models','ai','automation','automate'},
    {'finance','financial','bank','banking','lending','credit'},
    {'water','utility','utilities','gas','pipeline','network'},
    {'document','documents','text','knowledge','record','records','information'},
    {'cloud','platform','infrastructure','digital','modernisation','modernization'},
]
VALID_ID = re.compile(r'^[\w-]+$', re.UNICODE)


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def fp(text):
    return sha256(text.encode('utf-8')).hexdigest()


def json_read(path, default=None):
    if not Path(path).exists():
        return default
    return json.loads(Path(path).read_text(encoding='utf-8'))


def json_write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def log(event):
    path = ROOT / 'reports' / 'agent_log.jsonl'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as out:
        out.write(json.dumps({'at': now(), **event}, ensure_ascii=False) + '\n')


def files():
    path = ROOT / 'corpus'
    return sorted([p for p in path.glob('*.txt') if p.is_file()], key=lambda p: p.name.casefold())


def case_path(case_id):
    if not VALID_ID.fullmatch(case_id):
        raise ValueError('Invalid case ID')
    path = ROOT / 'corpus' / f'{case_id}.txt'
    if not path.is_file():
        raise FileNotFoundError(f'Case not found: {case_id}')
    return path


def source(case_id):
    return case_path(case_id).read_text(encoding='utf-8-sig')


def lineno_text(case_id):
    return source(case_id).splitlines()


def base_record(case_id):
    return {
        'case_id': case_id, 'language': 'unknown', 'sector': None, 'country': None,
        'problem': None, 'capabilities': [], 'scale_outcomes': [],
        'reuse': [], 'summary': [], 'sensitivity_flags': [],
        'disclosure_status': 'unknown',
        '_instructions': 'Each populated factual field needs source evidence. Keep unknowns empty. Never infer numbers.'
    }


def evidence_refs_for(value):
    if isinstance(value, dict):
        return value.get('evidence', [])
    return []


def verify_evidence(case_id, evidence):
    lines = lineno_text(case_id)
    if not isinstance(evidence, list) or not evidence:
        raise ValueError(f'{case_id}: missing source evidence')
    for item in evidence:
        if not isinstance(item, dict):
            raise ValueError(f'{case_id}: evidence must be an object')
        a, b, snippet = item.get('line_start'), item.get('line_end'), item.get('quote')
        if not isinstance(a, int) or not isinstance(b, int) or a < 1 or a > b or b > len(lines):
            raise ValueError(f'{case_id}: invalid line range {a}-{b}')
        original = ' '.join(' '.join(lines[a-1:b]).split())
        quoted = ' '.join(str(snippet or '').split())
        if len(quoted) < 8 or quoted not in original:
            raise ValueError(f'{case_id}: evidence quote does not occur verbatim at lines {a}-{b}: {quoted!r}')


def verify_review(case_id, record):
    if record.get('case_id') != case_id:
        raise ValueError('Case ID mismatch')
    for key in ('sector', 'country', 'problem'):
        entry = record.get(key)
        if entry is not None:
            if not isinstance(entry, dict) or not str(entry.get('text', '')).strip():
                raise ValueError(f'{key} must be an object with text and evidence')
            verify_evidence(case_id, evidence_refs_for(entry))
    for key in ('capabilities', 'scale_outcomes', 'reuse'):
        for entry in record.get(key, []):
            if not isinstance(entry, dict) or not str(entry.get('text', '')).strip():
                raise ValueError(f'{key}: each fact needs text and evidence')
            verify_evidence(case_id, evidence_refs_for(entry))
    summaries = record.get('summary', [])
    if summaries and len(summaries) != 2:
        raise ValueError('Reviewed summary must contain exactly two source-backed sentences')
    for s in summaries:
        if not isinstance(s, dict) or not str(s.get('text','')).strip():
            raise ValueError('Summary sentence needs text and evidence')
        verify_evidence(case_id, evidence_refs_for(s))
    if record.get('disclosure_status') not in ('unknown','internal_only','client_approved'):
        raise ValueError('disclosure_status must be unknown, internal_only, or client_approved')
    if not isinstance(record.get('sensitivity_flags', []), list):
        raise ValueError('sensitivity_flags must be a list')
    return True


def reviewed_record(case_id):
    path = ROOT / 'enriched' / 'reviewed' / f'{case_id}.json'
    result = json_read(path)
    if not result:
        return None
    try:
        verify_review(case_id, result)
        # A syntactically valid enrichment record is NOT human reviewed.
        # Require a named approver, review timestamp, and unchanged source.
        if not isinstance(result.get('_reviewer'), str) or not result['_reviewer'].strip():
            return None
        if not isinstance(result.get('_reviewed_at'), str) or not result['_reviewed_at'].strip():
            return None
        if result.get('_source_sha256') != fp(source(case_id)):
            return None
    except (ValueError, FileNotFoundError):
        return None
    return result


def rec_text(record):
    if record is None:
        return ''
    chunks = []
    for key in ('sector','country','problem','capabilities','scale_outcomes','reuse'):
        value = record.get(key)
        if isinstance(value, dict):
            chunks.append(str(value.get('text','')))
        elif isinstance(value, list):
            chunks.extend(str(e.get('text','')) for e in value if isinstance(e,dict))
    return ' '.join(chunks)


def toks(text):
    return [w.casefold() for w in re.findall(r'[^\W_]+', text, flags=re.UNICODE) if len(w) > 2 and w.casefold() not in STOP]


def aliases(token):
    out = {token}
    for group in ALIASES:
        if token in group:
            out |= group
    # light plural handling, not an English stemmer; never alters stored corpus.
    if token.endswith('ies'):
        out.add(token[:-3]+'y')
    elif token.endswith('s') and len(token)>4:
        out.add(token[:-1])
    else:
        out.add(token+'s')
    return out


def sentences_with_lines(text):
    """Return literal source snippets with approximate source line span."""
    result = []
    for i, line in enumerate(text.splitlines(), 1):
        cleaned = line.strip()
        if not cleaned:
            continue
        for piece in re.split(r'(?<=[.!?])\s+(?=[^\s])', cleaned):
            if piece.strip():
                result.append({'text': piece.strip(), 'lines': [i, i]})
    return result


def top_source_sentences(case_id, query, n=2):
    # Literal quotes only: safe when enrichment has not been reviewed.
    candidates = sentences_with_lines(source(case_id))
    qt = set(toks(query))
    ranking = []
    for i, c in enumerate(candidates):
        st = set(toks(c['text']))
        shared = sum(bool(st & aliases(t)) for t in qt)
        # Ignore extremely long strings likely to be headings/data dumps.
        penalty = max(0, len(c['text']) - 420) / 1000
        ranking.append((shared-penalty, -i, c))
    ranking.sort(reverse=True, key=lambda row: (row[0], row[1]))
    chosen = [c for _,_,c in ranking if len(c['text']) >= 15][:n]
    if len(chosen)<n:
        chosen.extend(c for c in candidates if c not in chosen)[:n-len(chosen)]
    return chosen


def chargrams(text):
    s = re.sub(r'\s+', ' ', text.casefold())[:1000]
    return set(s[i:i+3] for i in range(max(0,len(s)-2)))


def search(query, limit=3, threshold=0.30):
    qt = list(dict.fromkeys(toks(query)))
    if not qt:
        return {'query':query, 'results': [], 'no_strong_match':True, 'reason':'Enter a descriptive client problem.'}
    docs=[]
    for path in files():
        rid = path.stem
        raw=source(rid)
        rec=reviewed_record(rid)
        augmented=rec_text(rec)
        raw_counts=Counter(toks(raw))
        rec_counts=Counter(toks(augmented))
        docs.append((rid, raw_counts, rec_counts, raw, rec, augmented))
    if not docs:
        return {'query': query, 'results':[], 'no_strong_match':True,'reason':'No case-study text files found in corpus/.'}
    # IDF treats synonyms as one concept, so synonym groups cannot overwhelm matches.
    df={t:sum(1 for _,raw,rw,_,_,_ in docs if any(raw.get(a,0) or rw.get(a,0) for a in aliases(t))) for t in qt}
    idfs={t:1+math.log((len(docs)+1)/(df[t]+1)) for t in qt}
    weight_sum=sum(idfs.values())
    candidates=[]
    for cid,raw,review,original,rec,augmented in docs:
        matched=[]
        contributions=[]
        for t in qt:
            a=aliases(t)
            raw_tf=sum(raw.get(w,0) for w in a)
            review_tf=sum(review.get(w,0) for w in a)
            if raw_tf or review_tf:
                matched.append(t)
                tf=min(4,raw_tf + 2.5*review_tf)
                contributions.append(idfs[t]*(1+math.log(tf)))
        coverage=sum(idfs[t] for t in matched)/weight_sum if weight_sum else 0
        word_score=min(1.0, sum(contributions)/(2.5*weight_sum))
        snippets=sentences_with_lines(original)[:250]
        snippets.extend({'text':x,'lines':[]} for x in re.split(r'[.;]',augmented) if x.strip())
        qgrams=chargrams(query)
        fuzzy=max((len(qgrams & chargrams(s['text']))/len(qgrams | chargrams(s['text'])) for s in snippets if s['text'] and qgrams), default=0)
        score=0.65*coverage+0.25*word_score+0.10*fuzzy
        # A typo alone cannot force a match; at least one meaningful concept must match.
        eligibility=(len(matched) >= (2 if len(qt)>=4 else 1)) and score>=threshold
        candidates.append({'case_id':cid,'score':round(score,4),'coverage':round(coverage,3),'matched_concepts':matched,'eligible':eligibility, 'reviewed': bool(rec), 'review':rec})
    candidates.sort(key=lambda x:(-x['score'],x['case_id']))
    qualified=[c for c in candidates if c['eligible']]
    if not qualified:
        return {'query': query,'results':[], 'no_strong_match':True,
                'reason':'No result met the meaningful-term coverage and similarity threshold.',
                'near_misses':[{'case_id':c['case_id'],'score':c['score']} for c in candidates[:3]]}
    first=qualified[0]['score']
    chosen=[c for c in qualified if c['score'] >= max(threshold,first*0.55)][:limit]
    for c in chosen:
        cid=c['case_id']
        rec=c.pop('review')
        if rec and len(rec.get('summary',[]))==2:
            c['summary']=[{'text':s['text'],'evidence':s['evidence']} for s in rec['summary']]
            c['summary_type']='human-reviewed paraphrase'
        else:
            c['summary']=[{'text':s['text'],'evidence':[{'line_start':s['lines'][0],'line_end':s['lines'][1], 'quote':s['text']}]} for s in top_source_sentences(cid,query)]
            c['summary_type']='verbatim source excerpts'
        c['source_url']=f'/source/{quote(cid)}'
        c['reason']=f"Matched query concepts: {', '.join(c['matched_concepts'])}. " + ("Human-reviewed enrichment also informed the ranking." if c['reviewed'] else "Ranking uses original source text only.")
    return {'query':query,'results':chosen,'no_strong_match':False, 'reason':None}


def cmd_seed(args):
    made=0
    for path in files():
        p=ROOT/'enriched'/'drafts'/f'{path.stem}.json'
        if p.exists() and not args.overwrite:
            continue
        draft=base_record(path.stem)
        draft['_producer']='offline_empty_template_not_an_agent'
        draft['_source_sha256']=fp(source(path.stem))
        json_write(p,draft)
        made+=1
    print(f'Created {made} offline draft templates. These are NOT AI enrichment or human review.')


def cmd_agent(args):
    if not args.confirmed_approved_tool:
        raise SystemExit('Refusing: pass --confirmed-approved-tool only after checking this command is approved and keeps corpus within event rules.')
    prompt=(ROOT/'prompts'/'enrich_case.md').read_text(encoding='utf-8')
    argv=shlex.split(args.command)
    if not argv:
        raise SystemExit('No agent command supplied')
    produced=0
    for path in files():
        draft_path=ROOT/'enriched'/'drafts'/f'{path.stem}.json'
        if draft_path.exists() and not args.overwrite:
            continue
        payload={'prompt':prompt,'case_id':path.stem,'source_lines':[{'line':i,'text':line} for i,line in enumerate(source(path.stem).splitlines(),1)],'output_contract':'JSON record in prompts/enrich_case.md'}
        proc=subprocess.run(argv,input=json.dumps(payload,ensure_ascii=False),capture_output=True,text=True,timeout=args.timeout,check=False)
        if proc.returncode!=0:
            log({'stage':'enrichment_failed','case_id':path.stem,'command':argv,'return_code':proc.returncode, 'stderr_excerpt':proc.stderr[:400]})
            print(f'Failed {path.stem}: {proc.stderr[:120]}',file=sys.stderr)
            continue
        try:
            value=json.loads(proc.stdout)
            if not isinstance(value,dict) or value.get('case_id')!=path.stem:
                raise ValueError('Agent must emit a JSON object with matching case_id')
            value['_producer']='approved_agent_unreviewed'
            value['_model']=args.model
            value['_source_sha256']=fp(source(path.stem))
            json_write(draft_path,value)
            log({'stage':'agent_enrichment','case_id':path.stem,'skill':'skills/lynceus-enrichment/SKILL.md','model':args.model,'command':argv,'prompt_file':'prompts/enrich_case.md','prompt_sha256':fp(prompt),'source_sha256':fp(source(path.stem)),'draft_file':str(draft_path.relative_to(ROOT)),'draft_sha256':fp(json.dumps(value,sort_keys=True,ensure_ascii=False)),'human_review':'pending'})
            produced+=1
        except (ValueError,json.JSONDecodeError) as exc:
            log({'stage':'invalid_agent_output','case_id':path.stem,'error':str(exc)})
            print(f'Invalid output for {path.stem}: {exc}',file=sys.stderr)
    print(f'Created {produced} agent drafts, pending human review.')


def cmd_review(args):
    case_path(args.case_id)
    candidate=json_read(args.edited_file)
    if not candidate:
        raise SystemExit('Edited record JSON not found or empty')
    verify_review(args.case_id,candidate)
    candidate.pop('_instructions',None)
    candidate['_reviewer']=args.reviewer
    candidate['_reviewed_at']=now()
    candidate['_source_sha256']=fp(source(args.case_id))
    original=json_read(ROOT/'enriched'/'drafts'/f'{args.case_id}.json',{})
    if original.get('_source_sha256') and original['_source_sha256']!=candidate['_source_sha256']:
        raise SystemExit('Source changed since draft. Review against current source before approving.')
    target=ROOT/'enriched'/'reviewed'/f'{args.case_id}.json'
    json_write(target,candidate)
    changes={k:{'draft':original.get(k),'reviewed':candidate.get(k)} for k in ('language','sector','country','problem','capabilities','scale_outcomes','reuse','summary','sensitivity_flags','disclosure_status') if original.get(k)!=candidate.get(k)}
    log({'stage':'human_review','case_id':args.case_id,'reviewer':args.reviewer,'draft_file':f'enriched/drafts/{args.case_id}.json','reviewed_file':str(target.relative_to(ROOT)),'changes':changes,'source_sha256':candidate['_source_sha256']})
    print(f'Human-reviewed record saved: {target.relative_to(ROOT)}. Changed fields: {len(changes)}')


def cmd_search(args):
    r=search(args.question, limit=args.top, threshold=args.threshold)
    print(json.dumps(r,ensure_ascii=False,indent=2))


def cmd_evaluate(args):
    specs=json_read(args.test_set)
    if not isinstance(specs,list):
        raise SystemExit('Test set must be a JSON array')
    counts={'labelled_positive':0,'top3_hits':0,'labelled_negative':0,'correct_abstentions':0,'unlabelled':0}
    rows=[]
    for t in specs:
        query=t.get('question','')
        ids=t.get('expected_case_ids')
        expect_none=t.get('expect_no_match',False)
        result=search(query,limit=3,threshold=args.threshold)
        returned=[x['case_id'] for x in result['results']]
        record={'id':t.get('id'),'question':query,'returned_top3':returned,'expected_case_ids':ids,'expect_no_match':expect_none,'note':t.get('rationale',''),'preliminary_diagnosis':None}
        if not expect_none and (ids is None or len(ids)==0):
            counts['unlabelled']+=1
            record['status']='UNLABELLED: exclude from accuracy'
        elif expect_none:
            counts['labelled_negative']+=1
            ok=result['no_strong_match']
            counts['correct_abstentions']+=int(ok)
            record['status']='PASS' if ok else 'MISS'
            if not ok:
                record['preliminary_diagnosis']='False positive; inspect threshold, synonyms, and relevance. Human diagnosis required.'
        else:
            counts['labelled_positive']+=1
            ok=bool(set(returned)&set(ids))
            counts['top3_hits']+=int(ok)
            record['status']='PASS' if ok else 'MISS'
            if not ok:
                record['preliminary_diagnosis']='Inspect corpus relevance, missing enrichment, language support and ranker. Human diagnosis required.'
        rows.append(record)
    result={'at':now(),'source_test_set':str(args.test_set),'threshold':args.threshold,'counts':counts,
        'recall_at_3': (counts['top3_hits']/counts['labelled_positive'] if counts['labelled_positive'] else None),
        'abstention_accuracy':(counts['correct_abstentions']/counts['labelled_negative'] if counts['labelled_negative'] else None),
        'note':'Unlabelled cases are excluded. Scores do not represent held-back judge results.', 'cases':rows}
    output=ROOT/'reports'/'evaluation.json'
    json_write(output,result)
    pct='NOT MEASURABLE' if result['recall_at_3'] is None else f"{result['recall_at_3']:.1%} ({counts['top3_hits']}/{counts['labelled_positive']})"
    lines=['# Lynceus Evaluation',f'Generated: {result["at"]}',f'**Recall@3: {pct}**',f'Unlabelled: {counts["unlabelled"]}',f'No-match accuracy: {result["abstention_accuracy"] if result["abstention_accuracy"] is not None else "NOT MEASURABLE"}', '', '## Individual test evidence']
    for r in rows:
        lines.extend([f'### {r["id"]}: {r["status"]}',f'Question: {r["question"]}',f'Expected: {r["expected_case_ids"]}; no-match expected: {r["expect_no_match"]}',f'Returned top 3: {r["returned_top3"]}',f'Rationale: {r["note"]}',f'Analysis: {r["preliminary_diagnosis"] or "Review ranking with original source."}',''])
    (ROOT/'reports'/'evaluation.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'Recall@3: {pct}. Detailed results: reports/evaluation.md')


def cmd_status(args):
    paths=files()
    review=[]
    for p in paths:
        rec=reviewed_record(p.stem)
        if rec: review.append(p.stem)
    print(json.dumps({'cases_loaded':len(paths),'reviewed_records':len(review),'reviewed_case_ids':review,'still_needs_review':len(paths)-len(review),'deadline':'14:45 Europe/London on 2026-11-11','uses_external_model_by_default':False},indent=2))


def render_html(body,title='Lynceus'):
    return ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>'+escape(title)+'</title><style>body{font:16px system-ui,Arial,sans-serif;max-width:900px;margin:32px auto;padding:0 20px;color:#17283d;background:#f8fafc}h1{font-size:34px;letter-spacing:-.5px}header{margin-bottom:25px}.muted{color:#64748b}.card{background:white;border:1px solid #dde5ee;border-radius:12px;padding:21px;margin:17px 0;box-shadow:0 3px 12px #10253d09}input{box-sizing:border-box;width:80%;padding:13px;font-size:16px;border:1px solid #98adc4;border-radius:8px}button{padding:13px 18px;background:#153d73;color:white;border:0;border-radius:8px;cursor:pointer}a{color:#194f91}code{font-size:13px}blockquote{margin:9px 0 14px 0;padding:9px 13px;background:#f1f5f9;border-left:3px solid #9aadc4}small{color:#64748b}table{border-collapse:collapse;width:100%}td{padding:4px;vertical-align:top;border-bottom:1px solid #eee}.warn{padding:14px;border:1px solid #e6c46c;background:#fffbeb;border-radius:10px}mark{background:#e1eafa}</style></head><body><header><a href="/">LYNCEUS</a><span class="muted"> · Local evidence-based knowledge search</span></header>'+body+'</body></html>')


def home(query=''):
    pre=f'<h1>Find relevant delivery experience</h1><p class="muted">Describe a client problem in plain English. Results show source-backed excerpts and explain which concepts matched.</p><form method="GET" action="/search"><input name="q" value="{escape(query,quote=True)}" placeholder="e.g. A bank needs to modernise 2,000 legacy validation rules" required><button>Find cases</button></form>'
    if not query:
        n=len(files())
        pre+=f'<p class="muted">{n} local cases loaded · No external model or network requests by default.</p>'
        if n==0:pre+='<div class="warn">No cases yet. Add the original, unmodified .txt files to the local <code>corpus/</code> folder. Do not upload the confidential corpus elsewhere.</div>'
        return render_html(pre)
    data=search(query)
    if data['no_strong_match']:
        pre+=f'<div class="warn"><strong>No strong match found.</strong> {escape(data["reason"])} The system does not invent or pad results.</div>'
    for i,row in enumerate(data['results'],1):
        pre+=f'<div class="card"><h2>{i}. Case {escape(row["case_id"])} <small>Rank score {row["score"]:.2f}</small></h2><p>{escape(row["reason"])}</p><small>{escape(row["summary_type"])}</small>'
        for item in row['summary']:
            evidence=item.get('evidence',[])
            spans=', '.join(f'L{e["line_start"]}–{e["line_end"]}' for e in evidence)
            pre+=f'<blockquote>{escape(item["text"])} <small>({escape(spans)})</small></blockquote>'
        pre+=f'<a href="{escape(row["source_url"],quote=True)}">Read original source with line numbers</a></div>'
    return render_html(pre)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url=urlparse(self.path)
        if url.path in ('/','/search'):
            q=parse_qs(url.query).get('q',[''])[0]
            self.respond(home(q),'text/html; charset=utf-8')
        elif url.path=='/api/search':
            q=parse_qs(url.query).get('q',[''])[0]
            self.respond(json.dumps(search(q),ensure_ascii=False,indent=2),'application/json; charset=utf-8')
        elif url.path.startswith('/source/'):
            case_id=unquote(url.path[len('/source/'):])
            try:
                rows=lineno_text(case_id)
                body=f'<h1>Case {escape(case_id)}</h1><p class="muted">Original, unmodified local source; line numbers enable verification.</p><div class="card"><table>'
                for i,line in enumerate(rows,1):
                    body+=f'<tr id="L{i}"><td style="width:60px"><a href="#L{i}">L{i}</a></td><td style="white-space:pre-wrap">{escape(line)}</td></tr>'
                body+='</table></div>'
                self.respond(render_html(body,case_id),'text/html; charset=utf-8')
            except (ValueError,FileNotFoundError):self.respond('Not found','text/plain',404)
        else:self.respond('Not found','text/plain',404)
    def respond(self,body,mime,status=200):
        b=body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(b)))
        self.send_header('Cache-Control','no-store')
        self.end_headers()
        self.wfile.write(b)
    def log_message(self,fmt,*args):
        pass


def cmd_serve(args):
    print(f'Lynceus local search at http://127.0.0.1:{args.port} | loaded {len(files())} local cases',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()


def main(argv=None):
    ap=argparse.ArgumentParser(description='Lynceus: source-grounded search for past deliveries')
    subs=ap.add_subparsers(dest='action',required=True)
    p=subs.add_parser('status',help='Count cases and reviewed enrichment'); p.set_defaults(func=cmd_status)
    p=subs.add_parser('seed',help='Create empty enrichment templates (NOT agent output)'); p.add_argument('--overwrite',action='store_true');p.set_defaults(func=cmd_seed)
    p=subs.add_parser('agent',help='Use an explicitly approved local agent command');p.add_argument('--command',required=True,help='Command that reads JSON from stdin and emits JSON on stdout');p.add_argument('--model',required=True);p.add_argument('--confirmed-approved-tool',action='store_true');p.add_argument('--overwrite',action='store_true');p.add_argument('--timeout',type=int,default=90);p.set_defaults(func=cmd_agent)
    p=subs.add_parser('review',help='Approve a human-edited record after verifying evidence');p.add_argument('case_id');p.add_argument('--reviewer',required=True);p.add_argument('--edited-file',type=Path,required=True);p.set_defaults(func=cmd_review)
    p=subs.add_parser('search',help='Command-line ranked search');p.add_argument('question');p.add_argument('--top',type=int,default=3);p.add_argument('--threshold',type=float,default=.30);p.set_defaults(func=cmd_search)
    p=subs.add_parser('evaluate',help='Run labelled cases; never invent results');p.add_argument('--test-set',type=Path,default=ROOT/'evaluation'/'test_set.json');p.add_argument('--threshold',type=float,default=.30);p.set_defaults(func=cmd_evaluate)
    p=subs.add_parser('serve',help='Run the local web interface');p.add_argument('--port',type=int,default=8000);p.set_defaults(func=cmd_serve)
    args=ap.parse_args(argv)
    args.func(args)

if __name__=='__main__':
    main()
