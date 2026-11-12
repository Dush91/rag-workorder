"""Thin wrapper around the Anthropic SDK so every pipeline step calls Claude the same way."""
import base64

import anthropic

from .config import MODEL

# Server-side fallback: if a safety classifier declines a request, the API
# retries it on a fallback model instead of returning a refusal.
FALLBACK = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}

_client = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    return _client


def _check(response):
    if response.stop_reason == "refusal":
        raise RuntimeError(f"Claude declined the request: {response.stop_details}")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Response was cut off at max_tokens")
    return response


def text(content, system=None, effort="low", max_tokens=4000) -> str:
    """Plain-text completion. `content` is a string or a list of content blocks."""
    response = _check(client().beta.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system or anthropic.NOT_GIVEN,
        messages=[{"role": "user", "content": content}],
        output_config={"effort": effort},
        **FALLBACK,
    ))
    return "".join(b.text for b in response.content if b.type == "text").strip()


def structured(content, schema, system=None, effort="medium", max_tokens=16000):
    """Completion constrained to a Pydantic schema; returns a validated instance."""
    response = _check(client().beta.messages.parse(
        model=MODEL,
        max_tokens=max_tokens,
        system=system or anthropic.NOT_GIVEN,
        messages=[{"role": "user", "content": content}],
        output_format=schema,
        output_config={"effort": effort},
        **FALLBACK,
    ))
    return response.parsed_output


def image_block(png: bytes) -> dict:
    return {"type": "image",
            "source": {"type": "base64", "media_type": "image/png",
                       "data": base64.standard_b64encode(png).decode()}}
