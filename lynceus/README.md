# Lynceus | Accenture Hackathon starter

A **local-first, source-grounded case-study search system** designed around the 11 November 2026 Spartan Hackathon participant brief. Pure Python 3.10+; no pip installs, external API keys or network calls needed for the baseline. The small localhost web app is a **working prototype**, not a claim of production security or tested relevance on the secret case corpus.

**This public-repo starter intentionally excludes actual case files, reviewed enrichments, results, internal answers, and completed test labels.**

**The private corpus is not supplied with this starter.** Put the team's original `*.txt` files under `corpus/` **inside the approved hackathon machine and team repository only**. Do not move the source files out of the event environment or paste them into an unapproved AI service. Do not alter those source files. Never publicly publish a populated copy of this directory.

See `docs/SECURE_HANDOFF.md` for the secure setup and evaluation-integrity checklist.

## One-command start

```bash
./run.sh
```

or on Windows PowerShell:

```powershell
py lynceus.py serve
```

Visit **http://127.0.0.1:8000**. Search a client problem; view ranked matches, exactly sourced excerpts, evidence line numbers, match explanations and original case files. For a scriptable search:

```bash
python3 lynceus.py search "A bank needs to modernise thousands of legacy validation rules"
```

No matching files? You will see an honest setup message, not fake case results.

## The first 20-60 minutes: do these IN ORDER

1. **Before building/tuning**: read a sample of the 30 original cases. Ask the product owner what good matches mean, how they handle confidential figures, what makes a useful cross-sector case, and what no-match should look like. Record answers in `docs/product_owner_notes.md`.
2. **FIRST artifact**: copy `evaluation/test_set.example.json` to `evaluation/test_set.json` and open it. The example contains **12 proposed question prompts** including two cross-sector, one multilingual candidate and a no-match test. Replace provisional prompts as necessary and fill each positive test's actual `expected_case_ids` from the real corpus. `null` IDs mean **NOT LABELLED** and are excluded from scored evaluation. At least 10 should be genuinely labelled BEFORE retrieval tuning. Ask the product owner to confirm the no-match case.
3. Copy the `*.txt` files into local `corpus/` without editing the originals. The system dynamically discovers any number of cases, including nine newly supplied ones.
4. Agree parallel roles using `docs/day_plan.md`. Assign agent, data, search, evaluation, BA, delivery and evidence/demo ownership.
5. Run the baseline, evaluate, review false negatives and make measured changes. Use enrichment from approved event AI tooling to improve cross-sector and multilingual retrieval.

## Commands

```bash
python3 lynceus.py status
python3 lynceus.py search "A water utility needs to find leaks with AI"
python3 lynceus.py evaluate --test-set evaluation/test_set.json
python3 lynceus.py seed
```

`seed` makes empty **offline templates**, explicitly NOT agent outputs. To call the **hackathon-approved** agent runner from the local machine, arrange for the runner to read one JSON object from standard input and emit one JSON object on standard output (see `prompts/enrich_case.md` and `skills/lynceus-enrichment/SKILL.md`). Only after your team checks that the command complies with the event's data-handling rules:

```bash
python3 lynceus.py agent --command "PATH_TO_APPROVED_AGENT_WRAPPER" --model "ACTUAL_MODEL_NAME" --confirmed-approved-tool
```

**Do not run this optional command with an unauthorised service.** No particular AI platform is presumed. The supplied adapter is a contract for your approved runner; its integration must be provided by the team. Agent-generated draft JSON lives in `enriched/drafts/`, which is never used directly in judge-facing search.

Human review: open the original `corpus/CASE_ID.txt` alongside `enriched/drafts/CASE_ID.json`; edit the JSON in a separate temporary reviewed file, then run:

```bash
python3 lynceus.py review CASE_ID --reviewer "Actual Reviewer" --edited-file /path/to/checked_record.json
```

Every factual field and sentence requires original-language exact source quotation and source line numbers. The verifier catches bad quote coordinates; the reviewer must separately check that **the paraphrased meaning and sensitivity flags are genuinely correct**. The program records draft/review differences. Review at least 10, prioritising all cases showcased to judges. The default web results use reviewed enrichment only; unreviewed cases can still be retrieved from raw sources with **verbatim** source excerpts, clearly labelled as such. This means some raw search outputs may remain awkward or in another language until reviewed enrichment is available.

## How matching works

- Preserve original text and citations. Build a fresh view each search (30-39 files is small enough), so newly arrived cases require **no re-index/restart**.
- Tokenise query and source, deduplicate query concepts, expand a modest set of domain-general vocabulary relationships (e.g. contact-centre/citizen triage; leak/methane; rules/validation), and apply a document-frequency weighted overlap score.
- Mix concept coverage, weighted match strength and character-gram resemblance. Human-reviewed plain-English enrichment receives higher term weight; useful for cross-industry or multilingual evidence.
- Require coverage and a configurable minimum score (`--threshold`, default 0.30); return up to three results, never force three where none qualify. **The score is a ranking heuristic, not a calibrated probability of relevance.**
- Source links open local numbered originals. Results give a match explanation and either a human-reviewed, evidence-linked two-sentence summary or two **verbatim** source extracts with line references.

**Important limitations:** Hand-built synonyms cannot equal robust semantic search; raw non-English text generally requires approved-agent English enrichment; exact source quote validation does not prove faithful summarisation; there is no user authentication; no claim of data-protection compliance beyond binding to loopback; no secure production hosting; the confidence threshold needs validation on labelled cases. For the hackathon, this intentionally optimises auditability and speed over embedding infrastructure.

## Evaluation, live round and proof

Use `python3 lynceus.py evaluate` after labels are completed. `reports/evaluation.md` and `.json` show **Recall@3** for labelled positive tests and no-match accuracy separately, with every result and preliminary issue flagged. Never present a score if no positive tests have real labels. The evaluator does **not** know judge-held answers; humans must document why misses occurred (missing enrichment, ranker, question ambiguity or no relevant case).

At **12:30**, add the nine new untouched files under `corpus/`. Run the same existing pipeline, review a useful subset if time allows, then evaluate with `evaluation/live_round_template.json` after replacing its five questions. Do **not** tune specifically for those five: log weaknesses and general fixes. Capture before/after case count using `status`; record that no manual editing of source files was needed.

The 13:15 client-ready note requires a separate human safety review and product-owner permission on client names, outcomes and figures. Use `docs/client_note_template.md`; do not automatically mark draft output safe for a client.

## Folder map

```text
corpus/                   original .txt case files copied locally by team
lynceus.py                search, app, evidence verification, review and evaluation
run.sh                    one-command launcher
evaluation/test_set.example.json   safe, unlabelled test-first template (copy to ignored test_set.json locally)
evaluation/live_round_template.json   held-back questions, not prelabelled
enriched/drafts/          optional agent drafts or labelled offline templates
enriched/reviewed/        human-reviewed records, verified references
prompts/enrich_case.md    no-hallucination prompt
skills/lynceus-enrichment/SKILL.md  skill definition
reports/                  evaluation and agent audit (generated locally)
docs/                     plan, evidence, demo, product-owner notes, client note
 tests/                   synthetic unit tests; never used to claim corpus accuracy
```

## Before commit/presentation

Run `python3 -m unittest discover -s tests -v`, `python3 lynceus.py status`, `python3 lynceus.py evaluate`, `./run.sh`; check at least one cross-industry query, one multilingual query, one no-match and line-level evidence manually. Check tracked files for confidentiality according to the hackathon's **existing approved repository rules** and commit small, meaningful changes. Make the last verified main-branch commit **before 14:45**. Present the seven-minute flow in `docs/demo_script.md`.

**Delivery truth:** This starter supplies implementation, scaffolding, prompts, preliminary test questions, evaluation tooling and documentation. It cannot truthfully provide real case mappings, enriched outcomes, an agent log of executions that never happened or empirical Recall@3 until the team's private corpus and approved tooling are used.

## Public-repository safety

The `.gitignore` deliberately excludes original cases, generated enrichments, evaluation results, actual test labels, and any answer keys. Keep those artefacts in the approved private team environment and do not force-add them with `git add -f`. Your team must check whether any populated audit/evidence pack is permitted for judging submission, using an approved **private** repository if necessary.
