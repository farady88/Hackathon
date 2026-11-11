"""Lynceus local web interface for Voyage semantic/hybrid search.

Runs only on 127.0.0.1. Uses the existing voyage_hybrid module and its
versioned local embedding cache; no source cases or API keys are included.

Usage:
  py voyage_search_app.py serve --mode hybrid --min-cosine 0.40 --approved-external-processing
  py voyage_search_app.py status

Do not serve confidential materials on public interfaces or commit data files.
"""
from __future__ import annotations

import argparse
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
from urllib.parse import parse_qs, quote, unquote, urlparse

import lynceus as base
import voyage_hybrid as vh

STYLES = """body{font:15px/1.55 system-ui,Segoe UI,Arial,sans-serif;color:#14273d;background:#f5f7fa;max-width:970px;margin:25px auto;padding:0 18px}a{color:#204d8c}h1{font-size:31px;margin:12px 0}h2{font-size:20px}h3{font-size:17px;margin:0}small,.muted{color:#526477}.top{display:flex;align-items:center;justify-content:space-between;gap:10px;border-bottom:1px solid #cdd7e2;padding:0 0 14px}.tag{padding:5px 9px;border-radius:14px;background:#e6ebf2;font-size:12px;color:#253f5e}.card{background:white;border:1px solid #d8e1eb;border-radius:12px;padding:19px;margin:15px 0;box-shadow:0 2px 9px #142b4310}.bar{display:flex;gap:8px;align-items:stretch}.bar input{flex:1;min-width:0}input,select{font:inherit;border:1px solid #aab9c9;border-radius:7px;padding:11px}button{font:inherit;background:#234e88;color:white;border:0;border-radius:7px;padding:12px 18px;cursor:pointer}.warning{border:1px solid #e5b76f;background:#fff8e9;padding:15px;border-radius:9px;margin:15px 0}blockquote{background:#f0f4f8;border-left:3px solid #9bb0c9;margin:10px 0;padding:12px 14px;white-space:pre-wrap}table{border-collapse:collapse;width:100%}td{vertical-align:top;border-bottom:1px solid #e5e9ef;padding:7px 5px;word-break:break-word}.line{color:#71849b;white-space:nowrap}.subtle{font-size:12px}.pill{background:#edf5f2;border-radius:14px;padding:3px 8px;font-size:12px}.review{background:#f8fbfe;border:1px solid #d3e1ed;border-radius:9px;padding:12px 15px;margin:12px 0}.review h3{font-size:15px;margin:6px 0 4px}.review ul{padding-left:20px;margin:5px 0 12px}.review li{margin:7px 0}.evidence{font-size:12px;color:#526477;margin-left:6px}.evidence a{white-space:nowrap}.note{font-size:13px;color:#425a71}.reviewed{background:#dcefe8}.unreviewed{background:#fff1db}code{background:#e7edf3;padding:2px 4px;border-radius:3px}footer{border-top:1px solid #cdd7e2;padding:18px 0;margin-top:30px;color:#667991;font-size:12px}"""


def page(inner: str, *, title: str = "Lynceus") -> str:
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{escape(title)}</title><style>{STYLES}</style></head><body>"
            "<div class='top'><a href='/'><strong>LYNCEUS</strong></a><span class='tag'>Private local search · human review required</span></div>"
            + inner + "<footer>Similarity is not confidence or factual proof. Only original source excerpts or human-reviewed claims are shown. Check disclosure restrictions before any client-facing use.</footer></body></html>")


def base_form(query: str, mode: str, min_cosine: float, count: int) -> str:
    return ("<h1>Discover reusable delivery experience</h1>"
            f"<p class='muted'>Search across <strong>{count}</strong> local case studies with Voyage multilingual embeddings and keyword matching.</p>"
            "<form method='GET' action='/search'><div class='bar'>"
            f"<input id='q' name='q' value='{escape(query, quote=True)}' required maxlength='2500' placeholder='Describe a client problem in plain English'>"
            "<button type='submit'>Search</button></div></form>"
            f"<p class='muted subtle'>Mode: {escape(mode)} · cosine minimum: {min_cosine:.2f} · Up to 3 results · no forced matches</p>")


def evidence_links(case_id: str, entry: dict) -> str:
    """Link reviewed claims to ORIGINAL local source lines; never trust raw HTML."""
    links = []
    for evidence in entry.get("evidence", []):
        if not isinstance(evidence, dict):
            continue
        a, b = evidence.get("line_start"), evidence.get("line_end")
        if not isinstance(a, int) or not isinstance(b, int) or a <= 0 or b < a:
            continue
        href = "/source/" + quote(case_id, safe="") + f"#L{a}"
        links.append(f"<a href='{escape(href, quote=True)}'>L{a}–L{b}</a>")
    return (" <span class='evidence'>Original source: " + ", ".join(links) + "</span>") if links else ""


def reviewed_details(case_id: str) -> str:
    """Show ONLY independently human-approved enrichments; ranking is untouched."""
    record = base.reviewed_record(case_id)
    if not record:
        return "<p class='note'><span class='pill unreviewed'>Not reviewed</span> Original source excerpts only; no AI-derived fact panel.</p>"
    sections = ["<div class='review'><p class='note'><span class='pill reviewed'>Human-reviewed</span> "
                "Extracted facts are checked against source quotations, but client-facing disclosure is not authorised by this badge.</p>"]
    for key, label in (("sector", "Sector"), ("country", "Country"), ("problem", "Client problem")):
        value = record.get(key)
        if isinstance(value, dict) and value.get("text"):
            sections.append(f"<h3>{label}</h3><p>{escape(str(value['text']))}{evidence_links(case_id, value)}</p>")
    for key, label in (("capabilities", "Delivered capabilities"), ("scale_outcomes", "Reported scale and outcomes"),
                       ("reuse", "Potential reuse — proposals, not proven outcomes")):
        entries = record.get(key)
        if not isinstance(entries, list) or not entries:
            continue
        sections.append(f"<h3>{label}</h3><ul>")
        for entry in entries[:8]:
            if isinstance(entry, dict) and entry.get("text"):
                sections.append(f"<li>{escape(str(entry['text']))}{evidence_links(case_id, entry)}</li>")
        sections.append("</ul>")
    if record.get("disclosure_status") != "client_approved":
        sections.append("<p class='note'><strong>Disclosure:</strong> not confirmed for client-facing use.</p>")
    sections.append("</div>")
    return "".join(sections)


def result_view(query: str, result: dict, *, mode: str, min_cosine: float, count: int) -> str:
    content = base_form(query, mode, min_cosine, count)
    if result.get("no_strong_match", False):
        content += ("<div class='warning'><strong>No strong match found.</strong> "
                    "We cannot identify a sufficiently relevant past delivery from these cases. "
                    "This is not proof that no such work exists.</div>")
    else:
        content += f"<p class='muted'>Showing {len(result.get('results', []))} ranked candidate(s). Every result requires human verification.</p>"
    for i, item in enumerate(result.get('results', []), 1):
        cid = str(item["case_id"])
        url = "/source/" + quote(cid, safe="")
        content += (f"<section class='card'><h2>{i}. {escape(cid)} "
                    f"<span class='tag'>Cosine {float(item['cosine_similarity']):.3f}</span></h2>"
                    f"<p>{escape(str(item.get('reason', '')))}</p>"
                    f"<p><span class='pill'>{escape(str(item.get('summary_type','')))}</span></p>")
        for sentence in item.get("summary", []):
            if not isinstance(sentence, dict):
                continue
            locations = ", ".join(f"L{e.get('line_start','?')}–L{e.get('line_end','?')}"
                                  for e in sentence.get("evidence", []) if isinstance(e, dict))
            content += (f"<blockquote>{escape(str(sentence.get('text', '')))}"
                        f" <small>({escape(locations)})</small></blockquote>")
        content += reviewed_details(cid)
        content += f"<a href='{url}'>Open original source with line references</a></section>"
    return page(content)


def source_view(case_id: str) -> str:
    rows = base.lineno_text(case_id)  # base.case_path validates allowed case ID and file presence
    content = f"<h1>Original source: {escape(case_id)}</h1><p class='muted'>Read-only local file; original line numbers preserved.</p><div class='card'><table>"
    for i, line in enumerate(rows, 1):
        content += (f"<tr id='L{i}'><td class='line'><a href='#L{i}'>L{i}</a></td>"
                    f"<td style='white-space:pre-wrap'>{escape(line)}</td></tr>")
    return page(content + "</table></div>", title=f"Source {case_id}")


def make_handler(*, model: str, mode: str, min_cosine: float, key: str):
    class Handler(BaseHTTPRequestHandler):
        def reply(self, content: str, mime: str = "text/html; charset=utf-8", status: int = 200):
            data = content.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store, private")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            url = urlparse(self.path)
            if url.path in ("/", "/search", "/api/search"):
                q = parse_qs(url.query).get("q", [""])[0].strip()
                if len(q) > 2500:
                    self.reply("Query too long", "text/plain", 400)
                    return
                if not q:
                    if url.path == "/api/search":
                        self.reply(json.dumps({"results": [], "reason": "Enter a question"}), "application/json; charset=utf-8")
                    else:
                        self.reply(page(base_form("", mode, min_cosine, len(base.files()))))
                    return
                try:
                    # Query cache makes repeated demo questions offline after first embedding call.
                    vector = vh.cached_query_vectors([q], model=model, key=key)[q]
                    result = vh.rank(q, model=model, mode=mode, min_cosine=min_cosine, key=key, query_vector=vector)
                except (RuntimeError, ValueError, OSError) as exc:
                    if url.path == "/api/search":
                        self.reply(json.dumps({"error": str(exc)}), "application/json; charset=utf-8", 503)
                    else:
                        self.reply(page(base_form(q, mode, min_cosine, len(base.files())) +
                                        f"<div class='warning'><strong>Search temporarily unavailable:</strong> {escape(str(exc))}</div>"), status=503)
                    return
                if url.path == "/api/search":
                    self.reply(json.dumps(result, ensure_ascii=False), "application/json; charset=utf-8")
                else:
                    self.reply(result_view(q, result, mode=mode, min_cosine=min_cosine, count=len(base.files())))
            elif url.path.startswith("/source/"):
                cid = unquote(url.path[len("/source/"):])
                try:
                    self.reply(source_view(cid))
                except (ValueError, FileNotFoundError):
                    self.reply("Source not found", "text/plain", 404)
            else:
                self.reply("Not found", "text/plain", 404)

        def log_message(self, fmt, *args):
            # Avoid accidentally printing confidential search questions into console logs.
            pass
    return Handler


def main(argv=None):
    ap = argparse.ArgumentParser(description="Local Lynceus Voyage web interface")
    ap.add_argument("action", choices=("status", "serve"), help="status is offline; serve starts the local browser UI")
    ap.add_argument("--mode", choices=("semantic", "hybrid"), default="hybrid")
    ap.add_argument("--model", default=vh.MODEL)
    ap.add_argument("--min-cosine", type=float, default=0.40)
    ap.add_argument("--port", type=int, default=8001)
    ap.add_argument("--approved-external-processing", action="store_true")
    args = ap.parse_args(argv)
    try:
        if args.action == "status":
            try:
                indexed = len(vh.checked_index(args.model))
                message = "current"
            except RuntimeError as ex:
                indexed = 0
                message = str(ex)
            print(json.dumps({"cases": len(base.files()), "indexed_cases": indexed, "index_state": message,
                              "mode": args.mode, "min_cosine": args.min_cosine}, indent=2))
            return 0
        key = vh.require_authorisation(args.approved_external_processing)
        if not -1 <= args.min_cosine <= 1:
            raise ValueError("Cosine threshold must be between -1 and 1")
        # One-command startup, including automatic indexing of new/changed local cases.
        new, total = vh.build_index(model=args.model, key=key)
        print(f"Lynceus Voyage app: {total} indexed cases, {new} new/changed; mode={args.mode}, threshold={args.min_cosine:.2f}")
        print(f"Open http://127.0.0.1:{args.port} (local computer only). Ctrl+C to stop.", flush=True)
        ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(model=args.model, mode=args.mode, min_cosine=args.min_cosine, key=key)).serve_forever()
        return 0
    except KeyboardInterrupt:
        print("Stopped.")
        return 0
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
