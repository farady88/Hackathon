#how we call the model

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

MODEL = os.environ.get("LYNCEUS_MODEL", "claude-haiku-4-5-20251001")
MAX_TOKENS = 16000


def get_client():
    """Anthropic client. Imported here, not at module level, so grounding and the
    tests run without the SDK or a key."""
    import anthropic
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Export it or put it in a .env file at the repo root, "
            "once the team has confirmed this API is approved for the corpus.")
    # The SDK itself retries 429, 5xx, timeouts and connection errors.
    return anthropic.Anthropic(max_retries=3, timeout=120)


def call_model(client, system, messages, tools):
    return client.messages.create(model=MODEL, max_tokens=MAX_TOKENS, system=system,
                                  messages=messages, tools=tools)
