"""Difficulty router — classify a turn into a model tier and resolve a backend.

Tiers: reflex (cheap/instant), workhorse (balanced), deep (heavy reasoning),
vision (image input). Classification is heuristic for now — fast and free — and
can be upgraded to a cheap-model classifier later. Resolution reads config's
ROUTING table and falls back gracefully when a provider's key is missing.
"""
from __future__ import annotations

import os

import config
from core import llm

# Words that signal a genuinely hard / reasoning-heavy ask → deep tier.
_DEEP_HINTS = (
    "why", "explain", "debug", "fix the", "design", "architect", "plan ",
    "solve", "prove", "optimi", "refactor", "algorithm", "complexity",
    "compare", "analyse", "analyze", "strategy", "trade-off", "tradeoff",
    "implement", "write a ", "build a ", "leetcode", "dynamic programming",
    "system design", "step by step", "walk me through", "figure out",
)
# Short, imperative command starts → reflex tier.
_COMMAND_STARTS = (
    "open ", "launch ", "start ", "play ", "pause ", "stop ", "close ",
    "add ", "remove ", "delete ", "mark ", "set ", "show ", "list ", "what time",
    "what's the time", "screenshot", "take a screenshot", "switch to", "go to",
    "remind me", "note ", "mute", "volume",
)

_DEEP_MIN_WORDS = 38  # long asks tend to be complex

_backends: dict[str, llm.Backend] = {}


def classify(text: str, has_image: bool = False) -> str:
    if has_image:
        return "vision"
    t = (text or "").lower().strip()
    if not t:
        return "reflex"
    words = t.split()
    if any(h in t for h in _DEEP_HINTS) or len(words) >= _DEEP_MIN_WORDS:
        return "deep"
    if len(words) <= 8 or t.startswith(_COMMAND_STARTS):
        return "reflex"
    return "workhorse"


def _has_key(provider: str) -> bool:
    cfg = config.LLM_PROVIDERS.get(provider, {})
    env = cfg.get("key_env")
    return env is None or bool(os.getenv(env))


def _backend(provider: str) -> llm.Backend:
    if provider in _backends:
        return _backends[provider]
    cfg = config.LLM_PROVIDERS[provider]
    key = os.getenv(cfg["key_env"]) if cfg.get("key_env") else None
    if cfg["kind"] == "anthropic":
        b: llm.Backend = llm.AnthropicBackend(api_key=key)
    else:
        b = llm.OpenAICompatBackend(base_url=cfg["base_url"], api_key=key)
    _backends[provider] = b
    return b


def _first_available() -> tuple[str, str]:
    """Pick any provider that has a key (FALLBACK first), for graceful degrade."""
    fb_provider, fb_model = config.FALLBACK
    if _has_key(fb_provider):
        return fb_provider, fb_model
    for tier_provider, tier_model in config.ROUTING.values():
        if _has_key(tier_provider):
            return tier_provider, tier_model
    return fb_provider, fb_model  # nothing keyed — let it error informatively


def resolve(text: str, has_image: bool = False) -> tuple[llm.Backend, str, str, str]:
    """Return (backend, model, provider, tier) for a turn."""
    if not config.ROUTING_ENABLED:
        provider, model = config.FALLBACK
    else:
        tier = classify(text, has_image)
        provider, model = config.ROUTING.get(tier, config.FALLBACK)
        if not _has_key(provider):
            provider, model = _first_available()
        return _backend(provider), model, provider, tier
    return _backend(provider), model, provider, "single"
