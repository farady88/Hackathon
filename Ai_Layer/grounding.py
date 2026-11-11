"Checks on generated answers. Pure functions: no network, no model"

"""Failure - ungrounded hallucination: sentences that carry no citation at all.

Failure - citation drift: citations that point at the wrong source, or at no source

Failure - unsupported figure: a number in a sentence that none of its cited quotes contain.

A result is a plain dict:
    {"case_id", "why_matched", "summary": [{"text", "evidence": [{"line_start", "line_end", "quote"}]}]}
`sources` maps every case_id retrieved in this run to its source lines (1-based when cited).
"""
import re
import unicodedata

REFUSAL_SENTENCE = "The provided documents do not answer that question."
MIN_QUOTE_CHARS = 8  # same floor as verify_evidence in lynceus/lynceus.py


def _norm(text):
    return " ".join(unicodedata.normalize("NFC", str(text or "")).split())


def _figures(text):
    # Digits only, so 100.000 (id), 100,000 (en) and 100 000 (fr) compare equal.
    joined = re.sub(r"(?<=\d)[\s.,'](?=\d)", "", str(text or ""))
    return {str(int(n)) for n in re.findall(r"\d+", joined)}


def quote_found(quote, lines, line_start, line_end):
    """True when the quote occurs verbatim (whitespace-normalised) at the cited lines."""
    if not (isinstance(line_start, int) and isinstance(line_end, int)
            and 1 <= line_start <= line_end <= len(lines)):
        return False
    quoted = _norm(quote)
    return len(quoted) >= MIN_QUOTE_CHARS and quoted in _norm(" ".join(lines[line_start - 1:line_end]))


def find_uncited(result):
    return [f"sentence {i} has no citation"
            for i, s in enumerate(result.get("summary", []), 1) if not s.get("evidence")]


def find_citation_drift(result, sources):
    lines = sources.get(result.get("case_id"))
    if lines is None:
        return ["cites a case that was not retrieved in this run"]
    return [f"sentence {i}: quote is not verbatim at lines {e.get('line_start')}-{e.get('line_end')}: {e.get('quote')!r}"
            for i, s in enumerate(result.get("summary", []), 1)
            for e in s.get("evidence", [])
            if not quote_found(e.get("quote"), lines, e.get("line_start"), e.get("line_end"))]


def find_unsupported_figures(result):
    failures = []
    for i, s in enumerate(result.get("summary", []), 1):
        quoted = _figures(" ".join(str(e.get("quote", "")) for e in s.get("evidence", [])))
        missing = sorted(_figures(s.get("text")) - quoted)
        if missing:
            failures.append(f"sentence {i}: figure(s) {', '.join(missing)} not in its cited quote")
    return failures


def check_result(result, sources):
    return find_uncited(result) + find_citation_drift(result, sources) + find_unsupported_figures(result)


def check_answer(answer, sources):
    """Every grounding failure in an answer, as readable strings. Empty list means grounded."""
    return [f"{r.get('case_id')}: {f}" for r in answer.get("results", []) for f in check_result(r, sources)]
