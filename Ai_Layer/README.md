# Lynceus AI layer

A search agent that takes a lead's question in plain English and returns up to three past deliveries, each with a two-sentence summary, the reason it matched and a link to the source. Every sentence carries a verbatim quote and line numbers, and code checks those citations before anything is shown. When nothing fits, it says so.

## Files

| File | What it does |
|---|---|
| `agent.py` | The tool-use loop. The model can call `search_cases`, `read_case` and `submit_answer`; the loop checks the submitted answer and returns the same result shape as `lynceus.search()`. |
| `grounding.py` | Pure checks on an answer: sentences with no citation, citations that do not match the source, figures that are not in the cited quote. No network, no model. |
| `llm.py` | How the model is called: model name, client, one `call_model` function. |
| `knowledge_store.py` | Where case text comes from. `CorpusStore` reads the raw `.txt` files today; `EmbeddedStore` is the stub for the embedded corpus. |
| `evaluate.py` | Runs the agent over `tests/test_cases.json` and reports Recall@3 and no-match accuracy. |
| `tests/test_agent.py` | Offline tests with a scripted fake model. |

## Run it

Use `python` (3.12). On this machine `py` starts Python 3.14, which does not have the packages.

```bash
python -m pip install -r Ai_Layer/requirements.txt
python -m unittest discover -s Ai_Layer/tests -v        # offline, no key needed
python Ai_Layer/agent.py "A bank needs to modernise thousands of legacy business rules"
python Ai_Layer/evaluate.py
```

The last two call the model and need `ANTHROPIC_API_KEY`, exported or in a `.env` file at the repo root (`.env` is gitignored). The brief says to use only the approved agent tooling, so confirm this API is approved before sending case text. Set `LYNCEUS_MODEL` to use a model other than `claude-haiku-4-5-20251001`.

## How an answer is checked

1. The model submits an answer through `submit_answer`.
2. `grounding.check_answer` verifies every quote against the lines it cites, and every figure against its quote. A case the model was never shown cannot be cited.
3. If anything fails, the model gets the list of problems and one more attempt.
4. If it still fails: a result with a missing or wrong citation is dropped; a result whose only problem is a figure is shown as verbatim source excerpts.

Each result is labelled `agent draft, citations verified, not human-reviewed` or `verbatim source excerpts`. Set `ALLOW_UNREVIEWED_SUMMARIES = False` in `agent.py` to show only verbatim excerpts.

Every run appends one line to `Ai_Layer/logs/agent_log.jsonl`: skill, model, prompt hash, question, tool calls, what the first submission was rejected for, and the output.

## Plugging in the embedded corpus

The agent only needs two methods from a store:

```python
search(query: str, k: int) -> list[Hit]   # Hit(case_id, text, line_start, line_end, score)
get_case(case_id: str) -> list[str]       # untouched source lines
```

Implement `EmbeddedStore.search` in `knowledge_store.py`. `get_store()` switches to it as soon as `Ai_Layer/store/` exists (or the path in `LYNCEUS_STORE_PATH`). Nothing else changes. `get_case` stays on the raw files so citations always point at the original text.

Until then `CorpusStore` returns every case and the model ranks them. It reads `lynceus/corpus/` and every `lynceus_*/` folder at the repo root, so a new live-round folder is picked up without a code change. Set `LYNCEUS_CORPUS` to point it elsewhere.

## Limitations

- Not yet run against the real model: no key was available when this was built, so there is no Recall@3 figure.
- The fallback store sends every case to the model on each question. That is fine for a few dozen one-paragraph cases and will not scale beyond that without the embedded store.
- The figure check compares digits only. A number written in words, or in another numeral system, is not matched, and the result falls back to verbatim excerpts.
- `why_matched` is the model's reasoning and is not checked against the source.
- Summaries are not human-reviewed. Human-reviewed records from `lynceus/enriched/reviewed/` are not used here yet, because none exist.
- The web page in `lynceus/lynceus.py` is not wired to the agent. Results have `score: None`, which its page formats as a number, so that needs a small change when it is connected.
