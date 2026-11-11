"""Safely run one Lynceus Claude enrichment (no key or source text in logs).

Usage: py claude_one_case.py case-228 --confirmed-approved-tool
Claude must be an approved processing destination for these confidential files.
This file uses the existing Lynceus and Claude adapter; it is not a new model client.
"""
from __future__ import annotations
import argparse
import os
import sys


def run(case_id: str, model: str) -> int:
    import lynceus as L
    # Verify the file exists before initiating an API call.
    L.case_path(case_id)
    key = os.getenv('ANTHROPIC_API_KEY')
    if not key:
        print('Missing ANTHROPIC_API_KEY in this PowerShell session.', file=sys.stderr)
        return 2

    target = L.ROOT / 'enriched' / 'drafts' / f'{case_id}.json'
    prev = L.json_read(target)
    if prev and prev.get('_producer') != 'offline_empty_template_not_an_agent':
        print(f'Existing non-template draft preserved: {target.relative_to(L.ROOT)}')
        print('Review it rather than overwriting it.')
        return 0

    prompt = (L.ROOT / 'prompts' / 'enrich_case.md').read_text(encoding='utf-8')
    source_text = L.source(case_id)
    payload = {
        'prompt': prompt, 'case_id': case_id,
        'source_lines': [{'line': i, 'text': line} for i, line in enumerate(source_text.splitlines(), 1)],
        'output_contract': 'JSON record in prompts/enrich_case.md',
    }
    # The adapter reads the selected model during import.
    os.environ['LYNCEUS_CLAUDE_MODEL'] = model
    import claude_enrichment_adapter as claude
    try:
        result = claude.ask_claude(payload, key)
    except (RuntimeError, ValueError, OSError) as exc:
        # The adapter intentionally sanitizes HTTP errors.
        print(f'No draft saved. Claude request failed: {exc}', file=sys.stderr)
        return 1
    result['_producer'] = 'approved_agent_unreviewed'
    result['_model'] = model
    result['_source_sha256'] = L.fp(source_text)
    L.json_write(target, result)
    try:
        L.verify_review(case_id, result)
        evidence_state = 'source quote coordinates validated; factual meaning still requires human review'
    except (ValueError, KeyError, TypeError):
        evidence_state = 'SOURCE EVIDENCE VALIDATION NEEDS CORRECTION by reviewer'
    L.log({
        'stage': 'agent_enrichment', 'case_id': case_id,
        'skill': 'skills/lynceus-enrichment/SKILL.md', 'model': model,
        'command': 'claude_one_case.py', 'prompt_file': 'prompts/enrich_case.md',
        'prompt_sha256': L.fp(prompt), 'source_sha256': L.fp(source_text),
        'draft_file': str(target.relative_to(L.ROOT)),
        'draft_sha256': L.fp(L.json.dumps(result, sort_keys=True, ensure_ascii=False)),
        'human_review': 'pending', 'evidence_status': evidence_state,
    })
    print(f'Claude draft saved: {target.relative_to(L.ROOT)}')
    print(evidence_state)
    print('This is NOT human-approved. Do not present draft claims as verified.')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description='Generate one unreviewed Lynceus Claude draft.')
    parser.add_argument('case_id', help='Existing case ID, e.g. case-228')
    parser.add_argument('--model', default='claude-sonnet-4-6')
    parser.add_argument('--confirmed-approved-tool', action='store_true')
    args = parser.parse_args()
    if not args.confirmed_approved_tool:
        parser.error('Requires --confirmed-approved-tool after organiser approval.')
    return run(args.case_id, args.model)


if __name__ == '__main__':
    sys.exit(main())
