# Lynceus: Five-hour delivery plan (11 November 2026, UK time)

The participant brief specifies 09:30–14:45; code freezes at 14:45. Adapt the schedule to actual progress rather than claiming milestones are complete.

| Time | Outcome | Owners |
|---|---|---|
| 09:30–09:50 | Roles, working machines, repo access; agree no-copy data boundary | Delivery + all |
| 09:50–10:30 | PO interview; inspect corpus; **commit labelled test set before tuning** | BA + Evaluation |
| 10:30–11:15 | In parallel: raw case loader, approved enrichment wrapper/skills, local search, evidence UI | Data, Agent, Search |
| 11:15–12:00 | Review >=10 enrichment records, confirm 2 cross-sector + multilingual + no-match examples | BA, Reviewers, Search |
| 12:00–12:30 | Run evaluation, inspect misses; prepare early evidence/demo; freeze baseline settings | Evaluation, Evidence, Delivery |
| 12:30–13:15 | Add 9 cases through unchanged pipeline; record held-back questions and results, inspect misses | All |
| 13:15–13:45 | Create one-page client-ready note for one held-back query; verify all facts + confidentiality | BA, Agent, Evidence |
| 13:45–14:25 | Finish honest Recall@3, case-by-case misses, design/limits evidence, demo | Evaluation, Evidence |
| 14:25–14:45 | Clean-start test, secrets/data check, push/merge verified files to team main | Delivery, All |
| After 14:45 | Seven-minute pitch; every person speaks; three-minute questions | All |

## Suggested role assignment

- Delivery lead: times, priorities, integration, stopping unnecessary work.
- Business analyst: PO interview, **test-first** questions, correct ground-truth IDs.
- Data engineer: read-only file ingest, UTF-8 and multilingual resilience.
- Search engineer: query matching, scores, abstention and why-ranked explanation.
- Agent engineer: approved skill/prompt, enrichment drafts and complete agent log.
- Evaluation lead: Recall@3, negatives, misses and evidence captures.
- Evidence/demo lead: one-page design, live-round log, seven-minute script.

Small team: pair BA with Evaluation; Data with Search; Agent with Evidence. Every member still speaks in demo.

## Highest-value cuts if behind

Cut fancy UI, embeddings, animated dashboards, extra charts and generic chatbot capabilities first. Do **not** cut test-first labels, source citation checks, human-review evidence, honest no-match, language case, clean-start reproducibility or complete misses. Judges value relevance and trust more than polish.
