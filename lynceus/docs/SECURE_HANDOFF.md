# Lynceus secure handoff (11 November 2026)

## What is included

This code-only starter includes a local web search interface, source citation verification, optional approved-agent input/output contract, human-review audit trail, an evaluation runner, 12 synthetic unit tests, and a provisional question sheet.

**No confidential case study, annotated reference deck, filename-to-answer map, or held-back answer is included.** Treat this project as a *starter*, not as a demonstrated high-recall search application.

## Approved environment only

The participant brief requires source material to remain on the team's Sparta Global machine/repository and to be processed only by the agent tools approved for the event. Do not use any external model, upload public repositories, copy case text to personal services, or import an answer key into the retrieval or evaluation pipeline.

Place the supplied **30 original case-*.txt files** directly inside `corpus/` on an approved team machine. Leave every source file unchanged. Do not add `__MACOSX` metadata files or Apple's `._*` sidecar entries.

## Five-minute technical checks

1. `python3 -m unittest discover -s tests -v` — all synthetic tests should pass.
2. `python3 lynceus.py status` — initially 30 cases; nine more during the live round.
3. `python3 lynceus.py search "A company needs to modernise legacy validation rules"` — inspect ranking, then compare to original source manually.
4. `python3 lynceus.py evaluate` — accuracy is **not measurable** until the product-owner-reviewed test set contains actual labels; don't report provisional labels as evidence.
5. `./run.sh` (macOS/Linux) or `py lynceus.py serve` (Windows), then open `http://127.0.0.1:8000` locally.

## Evaluation integrity

- Create/confirm 10+ realistic questions and expected case IDs from **direct inspection** of permitted initial case files and product-owner input **before tuning retrieval**.
- Include two cross-industry, one multilingual and one genuine no-match question.
- Keep reference mappings and future live-round answers outside the running search application; don't backfit to live-round questions.
- Preserve agent drafts alongside reviewer-corrected records, noting model, skill, prompt, changes and exact evidence.
- Every source-backed summary must have a real reviewer recorded; changing original text after review invalidates the approval.
- Record honest top-three retrieval score, no-match performance, every miss and the underlying cause.

## Suggested work split

BA + evaluation: product-owner questions and labels; data + agent: ingest/enrich/review 10+ cases; search: ranking/threshold; demo/evidence: evaluate, record misses, run clean start, 7-minute demonstration. Commit code frequently only to the approved team repository.

## Limitations

The baseline does not itself call an AI model. Multilingual recall depends on approved-model enrichment and human review. This archive has no empirical case-retrieval score and no claim of compliance, production readiness, or completion of the event's four deliverables.
