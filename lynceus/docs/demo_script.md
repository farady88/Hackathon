# Seven-minute demo script (plus three-minute Q&A)

Do NOT deliver this script as a factual success claim until all bracketed items have been verified and inserted from real runs.

**0:00–0:35 — Delivery lead:** “Accenture has strong past delivery experience across industries, but it is hard to find because case studies use different vocabularies and languages. Lynceus connects client problems to relevant work, with evidence rather than marketing guesses.” Show clean start: `./run.sh`; show original case count.

**0:35–1:20 — Business analyst:** “Before building, we wrote [NUMBER] labelled questions with the product owner. We included cross-sector, multilingual and no-match cases. We froze the set at commit [HASH].” Display test set and actual expected case IDs.

**1:20–2:15 — Search engineer:** Enter a real, verified query. Show top-ranked case, matched concepts, two evidence-linked sentences, click original source. “The rank score is a search heuristic, not an invented accuracy probability.”

**2:15–3:00 — Data/agent engineer:** Show two **verified** cases that cross sector vocabulary, then an entry whose original is not English. Explain reviewed English metadata, source-language original lines and dynamic indexing. Avoid claiming success if the examples fail.

**3:00–3:50 — Agent engineer / reviewer:** Show actual `enriched/drafts/CASE.json` next to `enriched/reviewed/CASE.json`. Highlight one real correction and the exact source line. Show model, prompt version and human approval in `reports/agent_log.jsonl`.

**3:50–4:45 — Evaluation lead:** “On [N] prelabelled positive questions, the expected source appeared in the top three [H] times: Recall@3 = [H/N]. [NEG] of [NEG_TOTAL] no-match questions correctly abstained.” Show one miss, the real root cause and a general fix. Never hide misses or include unlabelled tests in N.

**4:45–5:45 — Live-round lead:** Show nine appended files, unchanged pipeline and their searchable presence. Display the five supplied questions, rankings and source checks. Report uncertainties honestly; no question-specific overfitting.

**5:45–6:30 — Evidence/client-note lead:** Show the one-page client note with approved lines, redacted identifiers, draft versus human corrections. “Anything not cleared for external use stays internal.”

**6:30–7:00 — Delivery lead:** “To productionise this, we'd need permissions and source licensing, secure access, better multilingual/semantic retrieval, reviewer workflows, benchmark calibration, monitoring and ongoing corpus updates. The prototype proves [ONLY WHAT WAS MEASURED].”

## Likely panel questions and concise answers

**Why not a vector DB?** With 30–39 cases and a five-hour deadline, a transparent, easily testable local baseline makes error diagnosis and evidence easier. Semantic embeddings would be an evaluated future option, not a default improvement without a test result.

**How do you prevent hallucination?** Only original quotations or human-reviewed paraphrases with verified source-line evidence appear; missing fields stay missing. Quote verification alone is not enough—reviewer checks meaning.

**How do you handle another language?** Approved enrichment produces a plain-English record grounded to original-language quotes; reviewed metadata becomes searchable while source stays unchanged. Until that is built, multilingual performance is a known limitation.

**Why can there be fewer than three results?** Returning weak matches as relevant is misleading. The engine abstains under a coverage/score floor. The floor must be validated on frozen labelled questions.

**How do you prove results?** Test labels before tuning, frozen set and independent source checks; report Recall@3 and no-match handling separately with every miss.

**What changed in the live round?** [Give actual record counts and examples.] The intended pipeline supports additional .txt files without manual editing, but verify real output rather than assert success in advance.
