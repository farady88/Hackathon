"""Optional Voyage AI document embeddings + hybrid retrieval for Lynceus.

This module deliberately DOES NOT run automatically. It requires a separately
approved external-processing flag because case texts are confidential. It never
commits, prints, or logs raw case contents or API credentials.

Requires only Python 3.10+ standard library. Keep the existing lexical search
as the unchanged baseline; use this CLI to evaluate an embedding-based variant.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request

import lynceus as base

MODEL = "voyage-4"
API_URL = "https://api.voyageai.com/v1/embeddings"
CACHE_DIR = base.ROOT / "enriched" / "vectors"


def require_authorisation(approved: bool) -> str:
    if not approved:
        raise RuntimeError(
            "External embedding is disabled until the organiser approves Voyage "
            "as a destination for confidential case text. Supply "
            "--approved-external-processing only after that approval."
        )
    key = os.environ.get("VOYAGE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("VOYAGE_API_KEY is unset. Enter it locally; never commit or paste it into chat.")
    return key


def embeddings(inputs: list[str], *, model: str, input_type: str, key: str) -> list[list[float]]:
    """Call Voyage REST API. No third-party SDK and no network calls during tests."""
    if not inputs:
        return []
    if input_type not in ("document", "query"):
        raise ValueError("input_type must be document or query")
    request = urllib.request.Request(
        API_URL,
        data=json.dumps({"input": inputs, "model": model, "input_type": input_type, "truncation": False}).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        # Never print server-provided bodies, which could contain input text or secrets.
        if exc.code == 429:
            retry_after = exc.headers.get('Retry-After') if exc.headers else None
            hint = (f' Suggested Retry-After: {retry_after} seconds.'
                    if retry_after and retry_after.isdecimal() else '')
            raise RuntimeError('Voyage HTTP 429: request/token rate limit reached. '
                               'Check account/project limits; do not repeatedly retry.' + hint) from None
        raise RuntimeError(f"Voyage API HTTP {exc.code}; check model, quota and permissions") from None
    except urllib.error.URLError:
        raise RuntimeError("Voyage API connection failed") from None
    data = payload.get("data")
    if not isinstance(data, list) or len(data) != len(inputs):
        raise RuntimeError("Voyage returned an unexpected number of vectors")
    vectors = [None] * len(inputs)
    for result in data:
        idx, vector = result.get("index"), result.get("embedding")
        if not isinstance(idx, int) or not (0 <= idx < len(inputs)) or vectors[idx] is not None:
            raise RuntimeError("Voyage returned invalid vector indices")
        if not isinstance(vector, list) or not vector or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in vector):
            raise RuntimeError("Voyage returned an invalid vector")
        vectors[idx] = [float(v) for v in vector]
    if any(x is None for x in vectors) or len({len(x) for x in vectors}) != 1:
        raise RuntimeError("Voyage vectors are missing or have inconsistent dimensions")
    return vectors


def index_path(model: str) -> Path:
    # Limit model name to a safe file component.
    if not model or not all(c.isalnum() or c in "-_" for c in model):
        raise ValueError("Invalid model name")
    return CACHE_DIR / f"{model}.json"


def load_index(model: str) -> dict:
    p = index_path(model)
    if not p.exists():
        raise RuntimeError("No vector index found. Run 'python voyage_hybrid.py index' first.")
    data = json.loads(p.read_text(encoding="utf-8"))
    if data.get("model") != model or not isinstance(data.get("entries"), dict):
        raise RuntimeError("Invalid or incompatible vector index")
    return data


def query_cache_path(model: str) -> Path:
    # Validate file component with the existing index path validation.
    index_path(model)
    return CACHE_DIR / f"{model}-query-vectors.json"


def cached_query_vectors(questions: list[str], *, model: str, key: str, batch_size: int = 32) -> dict[str, list[float]]:
    """Embed missing test questions in batches and reuse them between evaluation modes.

    Stores hashed query IDs and vectors only, never raw questions or API keys.
    Cache is local to the model, ignored by Git, and safe to reuse across modes.
    """
    if not 1 <= batch_size <= 32:
        raise ValueError("batch_size must be between 1 and 32")
    unique = list(dict.fromkeys(questions))
    if any(not isinstance(q, str) or not q.strip() for q in unique):
        raise ValueError('Evaluation questions must be nonempty strings')
    documents = checked_index(model)
    dimension = len(next(iter(documents.values()))['embedding'])
    path = query_cache_path(model)
    cache = {"schema":1,"model":model,"entries":{}}
    if path.exists():
        saved = json.loads(path.read_text(encoding='utf-8'))
        if saved.get('schema') == 1 and saved.get('model') == model and isinstance(saved.get('entries'), dict):
            cache = saved
    entries = cache['entries']
    missing = []
    for q in unique:
        v = entries.get(base.fp(q))
        if not isinstance(v,list) or len(v)!=dimension or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in v):
            missing.append(q)
    for n in range(0,len(missing),batch_size):
        group=missing[n:n+batch_size]
        vectors=embeddings(group,model=model,input_type='query',key=key)
        if any(len(v)!=dimension for v in vectors):
            raise RuntimeError('Query vectors do not match document vector dimensions')
        for q,v in zip(group,vectors):
            entries[base.fp(q)] = v
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(cache,ensure_ascii=False),encoding='utf-8')
    return {q:entries[base.fp(q)] for q in unique}


def cosine(x: list[float], y: list[float]) -> float:
    if len(x) != len(y) or not x:
        raise ValueError("Vector dimension mismatch")
    nx = math.sqrt(sum(a*a for a in x))
    ny = math.sqrt(sum(b*b for b in y))
    return sum(a*b for a, b in zip(x, y)) / (nx*ny) if nx > 0 and ny > 0 else 0.0


def build_index(*, model: str, key: str, batch_size: int = 12) -> tuple[int, int]:
    if not 1 <= batch_size <= 32:
        raise ValueError("batch_size must be between 1 and 32")
    paths = base.files()
    if not paths:
        raise RuntimeError("No case files in lynceus/corpus/. Nothing was sent to Voyage.")
    current = {p.stem: base.fp(base.source(p.stem)) for p in paths}
    path = index_path(model)
    if path.exists():
        cache = load_index(model)
    else:
        cache = {"schema": 1, "model": model, "entries": {}}
    # Exclude removed cases and invalidate changed case files.
    records = {cid: e for cid, e in cache["entries"].items()
               if cid in current and e.get("source_sha256") == current[cid]
               and isinstance(e.get("embedding"), list) and e["embedding"]}
    missing = [p for p in paths if p.stem not in records]
    for n in range(0, len(missing), batch_size):
        group = missing[n:n+batch_size]
        vectors = embeddings([base.source(p.stem) for p in group], model=model, input_type="document", key=key)
        for p, vector in zip(group, vectors):
            records[p.stem] = {"source_sha256": current[p.stem], "embedding": vector}
        # Persist each completed batch, so an API-rate-limit failure doesn't require re-embedding all cases.
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"schema":1, "model":model, "entries":records}, ensure_ascii=False), encoding="utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema":1,"model":model,"entries":records}, ensure_ascii=False),encoding="utf-8")
    return len(missing), len(records)


def checked_index(model: str) -> dict:
    stored = load_index(model)["entries"]
    current = {p.stem: base.fp(base.source(p.stem)) for p in base.files()}
    missing = [cid for cid, sha in current.items() if cid not in stored or stored[cid].get("source_sha256") != sha]
    if not current:
        raise RuntimeError("No case files found in corpus/.")
    if missing or set(stored) != set(current):
        raise RuntimeError(f"Vector index out of date for {len(missing)} case(s). Rerun 'index' (including after the live round).")
    return stored


def rank(query: str, *, model: str, key: str, mode: str = "hybrid", limit: int = 3,
         min_cosine: float = 0.5, query_vector: list[float] | None = None) -> dict:
    if not query.strip():
        return {"query":query, "mode":mode, "results":[], "no_strong_match":True}
    if not -1.0 <= min_cosine <= 1.0:
        raise ValueError("--min-cosine must be between -1 and 1")
    records = checked_index(model)
    vquery = query_vector if query_vector is not None else embeddings([query], model=model, input_type="query", key=key)[0]
    sims = {cid: cosine(vquery, entry["embedding"]) for cid, entry in records.items()}
    ranked_vectors = sorted(sims, key=lambda cid:(-sims[cid],cid))
    # Reuse existing tested lexical search, but do NOT lower the baseline threshold in saved reports.
    lexical = base.search(query, limit=len(records), threshold=0)
    ranked_lexical = [r["case_id"] for r in lexical["results"]]
    lex_rank = {cid:i+1 for i,cid in enumerate(ranked_lexical)}
    vector_rank = {cid:i+1 for i,cid in enumerate(ranked_vectors)}
    if mode == "semantic":
        sorted_ids = ranked_vectors
    elif mode == "hybrid":
        # Reciprocal rank fusion. Vector branch is weighted for multilingual use; keyword
        # contributes only when there is meaningful lexical overlap.
        sorted_ids = sorted(records, key=lambda cid:(
            -(1.0/(60+vector_rank[cid]) + (0.35/(60+lex_rank[cid]) if cid in lex_rank else 0)),
            -sims[cid], cid))
    else:
        raise ValueError("mode must be semantic or hybrid")
    # Absolute semantic similarity is NOT a calibrated relevance probability.
    # This conservative, user-configurable cutoff must be validated on negative examples.
    good = [cid for cid in sorted_ids if sims[cid] >= min_cosine][:max(0,limit)]
    results = []
    for cid in good:
        review = base.reviewed_record(cid)
        if review and len(review.get("summary", [])) == 2:
            summary = review["summary"]
            summary_type = "human-reviewed paraphrase"
        else:
            snippets = base.top_source_sentences(cid, query)
            summary = [{"text":s["text"], "evidence":[{"line_start":s["lines"][0],"line_end":s["lines"][1],"quote":s["text"]}]} for s in snippets]
            summary_type = "verbatim source excerpts"
        results.append({
            "case_id":cid,
            "cosine_similarity":round(sims[cid],4),
            "vector_rank":vector_rank[cid],
            "lexical_rank":lex_rank.get(cid),
            "source_url":f"/source/{cid}",
            "summary":summary,
            "summary_type":summary_type,
            "reason":f"Embedding similarity: {sims[cid]:.3f}; vector rank {vector_rank[cid]}; " +
                (f"lexical rank {lex_rank[cid]}. " if cid in lex_rank else "no qualifying lexical overlap. ") +
                "Semantic similarity is not evidence of a factual claim; check original source lines.",
        })
    return {"query":query,"mode":mode,"model":model,"min_cosine":min_cosine,
            "results":results,"no_strong_match":not results,
            "top_vector_candidates":[{"case_id":cid,"similarity":round(sims[cid],4)} for cid in ranked_vectors[:3]]}


def evaluate(*, test_set: Path, model: str, key: str, mode: str, min_cosine: float) -> dict:
    cases = json.loads(test_set.read_text(encoding="utf-8"))
    if not isinstance(cases, list):
        raise ValueError("Test set must be a JSON list")
    # One batched API call for all new questions; reuse cache for subsequent modes.
    qvectors = cached_query_vectors([item['question'] for item in cases],model=model,key=key)
    counts = {"positive":0,"hits":0,"negative":0,"abstentions":0,"unlabelled":0}
    rows = []
    for item in cases:
        want = item.get("expected_case_ids")
        no_match = bool(item.get("expect_no_match",False))
        result = rank(item["question"],model=model,key=key,mode=mode,min_cosine=min_cosine,
                      query_vector=qvectors[item['question']])
        got = [x["case_id"] for x in result["results"]]
        row = {"id":item.get("id"),"expected":want,"returned_top3":got,"no_match":no_match,
               "top_vector_candidates":result["top_vector_candidates"]}
        if no_match:
            counts["negative"] += 1
            if not got: counts["abstentions"] += 1
            row["status"] = "PASS" if not got else "FALSE_POSITIVE"
        elif want is None or not want:
            counts["unlabelled"] += 1
            row["status"] = "UNLABELLED"
        else:
            counts["positive"] += 1
            hit = bool(set(want) & set(got))
            if hit: counts["hits"] += 1
            row["status"] = "HIT" if hit else "MISS"
        rows.append(row)
    return {"created_at":datetime.now(timezone.utc).isoformat(),"model":model,"mode":mode,
            "min_cosine":min_cosine,"counts":counts,
            "recall_at_3":counts["hits"]/counts["positive"] if counts["positive"] else None,
            "no_match_accuracy":counts["abstentions"]/counts["negative"] if counts["negative"] else None,
            "note":"Experimental comparison only. Labels require independent confirmation; do not tune to held-back questions.",
            "cases":rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Voyage embeddings + hybrid Lynceus search (explicit external-processing approval required)")
    parser.add_argument("action",choices=("index","search","evaluate"))
    parser.add_argument("question",nargs="?",help="Question for search action")
    parser.add_argument("--model",default=MODEL)
    parser.add_argument("--mode",choices=("semantic","hybrid"),default="hybrid")
    parser.add_argument("--min-cosine",type=float,default=0.5)
    parser.add_argument("--test-set",type=Path,default=base.ROOT/"evaluation"/"test_set.json")
    parser.add_argument("--batch-size",type=int,default=12)
    parser.add_argument("--approved-external-processing",action="store_true")
    args=parser.parse_args(argv)
    try:
        key = require_authorisation(args.approved_external_processing)
        if args.action == "index":
            new,total = build_index(model=args.model,key=key,batch_size=args.batch_size)
            print(f"Indexed {total} cases with {args.model}; API-embedded {new} new/changed cases. Cache remains local and ignored by Git.")
        elif args.action == "search":
            if not args.question:
                parser.error("search requires a question")
            print(json.dumps(rank(args.question,model=args.model,key=key,mode=args.mode,min_cosine=args.min_cosine),indent=2,ensure_ascii=False))
        else:
            report = evaluate(test_set=args.test_set,model=args.model,key=key,mode=args.mode,min_cosine=args.min_cosine)
            path=base.ROOT/"reports"/f"voyage_{args.mode}_evaluation.json"
            base.json_write(path,report)
            print(f"{args.mode} Recall@3: {report['recall_at_3']}; no-match accuracy: {report['no_match_accuracy']}. Saved {path}.")
    except (ValueError,RuntimeError,OSError) as exc:
        print(f"Error: {exc}",file=sys.stderr)
        raise SystemExit(1) from None


if __name__=="__main__":
    main()
