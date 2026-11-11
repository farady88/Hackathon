---
name: lynceus-enrichment
purpose: Extract structured, line-evidenced case-study facts from an existing local source text
approval: Use ONLY with the official hackathon-approved agent tools
---

# Lynceus Enrichment Skill

**When:** Every new local case-study .txt file must become searchable; also the nine live-round additions.

**Inputs:** Case ID; numbered original lines; no network copy of case text.

**Prompt:** `prompts/enrich_case.md`. The model must output exactly one JSON record, never a free-form answer.

**Outputs:** `enriched/drafts/CASE_ID.json` (agent draft, not judge-facing), with fields: original language, sector, country, client problem, capabilities/techniques, quantitative scale/outcomes, potential reuse, two-sentence evidence-backed summary, confidentiality flags and source line evidence.

**Guardrails:** No assumptions; unknown fields stay unknown; quote a verbatim source substring for every populated factual field; do not mark any client-facing permission as approved. A person must check every published draft against the original before approval. Keep original corpus unchanged.

**Human gate:** Reviewer saves an edited JSON record then runs `python3 lynceus.py review CASE_ID --reviewer "Name" --edited-file PATH`. The application verifies quote locations and logs the changed fields. This validation detects fabricated citations but it does NOT prove that a paraphrase is semantically accurate: human review remains essential.

**Agent log:** `reports/agent_log.jsonl` records model, prompt filename/hash, draft hashes and human changes. Use only an officially approved agent runner. The default app has no agent transport or outbound requests.
