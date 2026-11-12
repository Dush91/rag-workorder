"""Thin wrapper so every pipeline step calls an LLM the same way.

`claude-*` model IDs use the Anthropic API (adaptive thinking, effort, structured outputs,
server-side refusal fallback). Any other model ID uses Doubleword's OpenAI-compatible API
(open-weight models such as DeepSeek, GLM, Kimi, Qwen), with JSON-schema structured output.
"""
import base64
import os
import threading
import time

import anthropic

from .config import DOUBLEWORD_BASE_URL, MODEL

# Server-side fallback: if a safety classifier declines a request, the API
# retries it on a fallback model instead of returning a refusal.
FALLBACK = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}

_client = None
_oai = None
_trace = threading.local()  # per-thread call log, used by the eval runner


def is_claude(model: str) -> bool:
    return model.startswith("claude-")


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # API key env var, or an `ant auth login` profile
    return _client


def oai():
    global _oai
    if _oai is None:
        from openai import OpenAI
        _oai = OpenAI(base_url=DOUBLEWORD_BASE_URL, api_key=os.environ["DOUBLEWORD_API_KEY"],
                      timeout=600, max_retries=4)
    return _oai


def start_recording() -> list:
    """Record every LLM call made on this thread (model, usage, stop_reason, latency)."""
    _trace.calls = []
    return _trace.calls


def _log(requested, served, stop, started, inp, out, cache_read=0, cache_write=0):
    calls = getattr(_trace, "calls", None)
    if calls is not None:
        calls.append({"requested_model": requested, "model": served, "stop_reason": stop,
                      "latency_s": round(time.time() - started, 2),
                      "usage": {"input_tokens": inp, "output_tokens": out,
                                "cache_read_input_tokens": cache_read,
                                "cache_creation_input_tokens": cache_write}})


def _check(stop_reason, details=None):
    if stop_reason == "refusal":
        raise RuntimeError(f"Model declined the request: {details}")
    if stop_reason in ("max_tokens", "length"):
        raise RuntimeError("Response was cut off at max_tokens")


# ---------- Anthropic ----------

def _claude(model, content, system, effort, max_tokens, schema=None):
    started = time.time()
    kwargs = dict(model=model, max_tokens=max_tokens, system=system or anthropic.NOT_GIVEN,
                  messages=[{"role": "user", "content": content}],
                  output_config={"effort": effort}, **FALLBACK)
    if schema is None:
        response = client().beta.messages.create(**kwargs)
    else:
        response = client().beta.messages.parse(output_format=schema, **kwargs)
    u = response.usage
    _log(model, response.model, response.stop_reason, started, u.input_tokens, u.output_tokens,
         u.cache_read_input_tokens or 0, u.cache_creation_input_tokens or 0)
    _check(response.stop_reason, response.stop_details)
    if schema is not None:
        return response.parsed_output
    return "".join(b.text for b in response.content if b.type == "text").strip()


# ---------- Doubleword (OpenAI-compatible) ----------

def _to_openai(content):
    """Anthropic-style content (string or blocks) -> OpenAI chat content."""
    if isinstance(content, str):
        return content
    parts = []
    for b in content:
        if b["type"] == "text":
            parts.append({"type": "text", "text": b["text"]})
        elif b["type"] == "image":
            src = b["source"]
            parts.append({"type": "image_url",
                          "image_url": {"url": f"data:{src['media_type']};base64,{src['data']}"}})
    return parts


def _openai(model, content, system, max_tokens, schema=None):
    started = time.time()
    messages = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": _to_openai(content)}]
    kwargs = dict(model=model, max_tokens=max_tokens, messages=messages)
    if schema is not None:
        kwargs["response_format"] = {"type": "json_schema", "json_schema": {
            "name": schema.__name__, "schema": schema.model_json_schema(), "strict": True}}
    r = oai().chat.completions.create(**kwargs)
    choice = r.choices[0]
    cached = getattr(getattr(r.usage, "prompt_tokens_details", None), "cached_tokens", 0) or 0
    _log(model, r.model, choice.finish_reason, started,
         r.usage.prompt_tokens - cached, r.usage.completion_tokens, cached)
    _check(choice.finish_reason)
    text = (choice.message.content or "").strip()
    return schema.model_validate_json(text) if schema is not None else text


# ---------- public API ----------

def text(content, system=None, effort="low", max_tokens=4000, model=MODEL) -> str:
    """Plain-text completion. `content` is a string or a list of content blocks."""
    if is_claude(model):
        return _claude(model, content, system, effort, max_tokens)
    return _openai(model, content, system, max(max_tokens, 8000))


def structured(content, schema, system=None, effort="medium", max_tokens=16000, model=MODEL):
    """Completion constrained to a Pydantic schema; returns a validated instance."""
    if is_claude(model):
        return _claude(model, content, system, effort, max_tokens, schema)
    return _openai(model, content, system, max_tokens, schema)


def image_block(png: bytes) -> dict:
    return {"type": "image",
            "source": {"type": "base64", "media_type": "image/png",
                       "data": base64.standard_b64encode(png).decode()}}
