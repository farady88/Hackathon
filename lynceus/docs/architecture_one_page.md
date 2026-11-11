# Lynceus — architecture and delivery decisions (one page)

**Business need.** Sales and delivery leaders should discover analogous past work from a plain-English problem, including projects in different sectors or languages. The output must explain relevance and only report source-supported claims.

**Data pipeline.** In the official team repository, untouched `corpus/*.txt` files remain the source of truth. The program reads them dynamically, retains 1-based source line numbers and creates no altered source text. The optional approved enrichment skill extracts sector, location, problem, methods, figures, potential reuse and original language, with verbatim evidence references.

**Human oversight.** AI output is stored in `enriched/drafts/`, separately from `enriched/reviewed/`. A named person edits and approves any judge-facing enrichment; exact evidence quote locations are program-validated and the semantic truth of each paraphrase is human-checked. Draft/review changes and the model/prompt metadata are logged. Unreviewed enrichment is excluded from ranked search, though untouched source extracts remain searchable.

**Search.** Local keyword/concept expansion and character-gram matching rank original source plus **reviewed** English metadata. The threshold and coverage gate permit an honest no-match, not fabricated certainty. The top three display why-ranked rationale, two evidence-linked sentences and original file links. Search recomputes dynamically, so new live-round cases can be added without a special ingest step.

**Evaluation.** A human-labelled, pre-build test set of at least 10 questions includes two cross-sector needs, one non-English and one no-match. Recall@3 measures labelled positive expected-case appearance in the top three. Negative-case abstention is measured separately. Every miss has a row for source, relevance, enrichment and ranker diagnostics. Held-back judge labels cannot be assumed or recreated.

**Why these trade-offs?** Thirty initial files and nine new files do not justify an untested vector database under a five-hour limit. Zero-install local search, auditable source grounding and honest evaluation are higher priority than interface complexity. It avoids unauthorised outbound AI use by default.

**Known limits.** Domain synonyms can be imprecise; source prose can be multilingual; no calibrated confidence probabilities; verbatim excerpts are not consistently sales-ready; human approval is required. Localhost demo has no authentication or secure multi-user service layer. Strong relevance and language performance must be verified with real labelled corpus cases.

**Path to Accenture use.** Confirm case reuse and client confidentiality rights, design least-privilege access controls and reviewer approvals, integrate approved multilingual semantic retrieval, build a versioned case index and audit logs, expand blind evals with real sales queries, test bias and leaking of confidential numbers, establish ownership for updates and monitor search quality, speed, cost and user feedback.
