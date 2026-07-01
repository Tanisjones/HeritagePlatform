from __future__ import annotations

import os
from dataclasses import dataclass, field
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.conf import settings

import yaml


class AIConfigError(Exception):
    pass


@dataclass(frozen=True)
class AIConfig:
    enabled: bool
    provider: str
    base_url: str
    model: str
    request_timeout_seconds: int
    temperature: float
    max_output_tokens: int
    allowed_operations: tuple[str, ...]
    prompts: dict[str, str]
    # Name of the env var holding the provider API key (e.g. "GEMINI_API_KEY"),
    # and the resolved key value. The key is read from the environment, never
    # from the committed ai.yaml. `api_key` is None when the env var is unset.
    api_key_env: str | None = None
    api_key: str | None = None
    # When true, contribution creation fires a (synchronous) AI call to generate
    # reviewable suggestions. Off by default so item creation stays instant and
    # never blocks on a provider round-trip; enable only with a fast provider.
    auto_suggest_on_create: bool = False
    # Per-model price table (USD per 1,000,000 tokens): {model: {"input": x, "output": y}}.
    # A "*" key is the fallback (covers Ollama / local models, priced at 0).
    pricing: dict[str, dict[str, float]] = field(default_factory=dict)

    def estimate_cost(
        self, model: str, input_tokens: int | None, output_tokens: int | None
    ) -> Decimal | None:
        """Estimated USD cost of a call, or None if tokens/pricing are unavailable.

        Looks up `model` in the price table, falling back to the "*" entry.
        Rates are per 1,000,000 tokens. Missing token counts contribute 0.
        """
        rates = self.pricing.get(model) or self.pricing.get("*")
        if not rates:
            return None
        if input_tokens is None and output_tokens is None:
            return None
        per_million = Decimal(1_000_000)
        cost = Decimal(0)
        cost += (Decimal(input_tokens or 0) / per_million) * Decimal(str(rates.get("input", 0)))
        cost += (Decimal(output_tokens or 0) / per_million) * Decimal(str(rates.get("output", 0)))
        # Quantize to the model field's 6 decimal places.
        return cost.quantize(Decimal("0.000001"))


def get_ai_config_path() -> Path:
    raw = os.getenv("AI_CONFIG_PATH") or getattr(settings, "AI_CONFIG_PATH", None)
    if not raw:
        base_dir = getattr(settings, "BASE_DIR", Path.cwd())
        return Path(base_dir) / "config" / "ai.yaml"

    path = Path(raw)
    if path.is_absolute():
        return path

    base_dir = getattr(settings, "BASE_DIR", Path.cwd())
    return Path(base_dir) / path


def reload_ai_config() -> AIConfig:
    _load_ai_config_cached.cache_clear()
    return load_ai_config()


def load_ai_config() -> AIConfig:
    return _load_ai_config_cached(str(get_ai_config_path()))


@lru_cache(maxsize=1)
def _load_ai_config_cached(path_str: str) -> AIConfig:
    path = Path(path_str)
    if not path.exists():
        raise AIConfigError(f"AI config file not found: {path} (set AI_CONFIG_PATH to override)")

    try:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise AIConfigError(f"Failed to parse AI config YAML: {path}: {exc}") from exc

    if not isinstance(parsed, dict):
        raise AIConfigError(f"AI config must be a mapping with a top-level 'ai:' key: {path}")

    ai = parsed.get("ai")
    if not isinstance(ai, dict):
        raise AIConfigError(f"AI config must include an 'ai:' mapping: {path}")

    enabled = _require_bool(ai, "enabled")
    provider = _require_str(ai, "provider")
    # base_url is only meaningful for the Ollama provider; hosted providers
    # (e.g. Gemini) ignore it, so it is optional unless provider == "ollama".
    if provider == "ollama":
        base_url = _require_str(ai, "base_url")
    else:
        base_url = ai.get("base_url") or ""
        if not isinstance(base_url, str):
            raise AIConfigError("AI config 'base_url' must be a string")
    model = _require_str(ai, "model")
    request_timeout_seconds = _require_int(ai, "request_timeout_seconds")
    temperature = _require_float(ai, "temperature")
    max_output_tokens = _require_int(ai, "max_output_tokens")

    allowed_operations = tuple(_require_list_of_str(ai, "allowed_operations"))
    prompts = _require_dict_str_str(ai, "prompts")

    missing_prompts = [op for op in allowed_operations if op not in prompts]
    if missing_prompts:
        raise AIConfigError(
            f"AI config missing prompt templates for: {', '.join(missing_prompts)} ({path})"
        )

    # Optional: name of the env var holding the provider API key. The key value
    # itself is resolved from the environment here and never stored in the YAML.
    api_key_env = ai.get("api_key_env")
    if api_key_env is not None and (not isinstance(api_key_env, str) or not api_key_env.strip()):
        raise AIConfigError("AI config 'api_key_env' must be a non-empty string when set")
    api_key = os.getenv(api_key_env) if api_key_env else None

    auto_suggest = ai.get("auto_suggest_on_create", False)
    if not isinstance(auto_suggest, bool):
        raise AIConfigError("AI config 'auto_suggest_on_create' must be a boolean")

    pricing = _parse_pricing(ai.get("pricing"))

    return AIConfig(
        enabled=enabled,
        provider=provider,
        base_url=base_url,
        model=model,
        request_timeout_seconds=request_timeout_seconds,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        allowed_operations=allowed_operations,
        prompts=prompts,
        api_key_env=api_key_env,
        api_key=api_key,
        auto_suggest_on_create=auto_suggest,
        pricing=pricing,
    )


def _parse_pricing(value: Any) -> dict[str, dict[str, float]]:
    """Optional {model: {input, output}} price table (USD per 1M tokens)."""
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise AIConfigError("AI config 'pricing' must be a mapping of model -> {input, output}")
    table: dict[str, dict[str, float]] = {}
    for model_key, rates in value.items():
        if not isinstance(model_key, str) or not model_key.strip():
            raise AIConfigError("AI config 'pricing' keys must be non-empty model-name strings")
        if not isinstance(rates, dict):
            raise AIConfigError(f"AI config 'pricing.{model_key}' must be a mapping with input/output")
        parsed_rates: dict[str, float] = {}
        for rate_key in ("input", "output"):
            rate = rates.get(rate_key, 0)
            if not isinstance(rate, (int, float)):
                raise AIConfigError(f"AI config 'pricing.{model_key}.{rate_key}' must be a number")
            parsed_rates[rate_key] = float(rate)
        table[model_key] = parsed_rates
    return table


def _require_str(obj: dict[str, Any], key: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AIConfigError(f"AI config '{key}' must be a non-empty string")
    return value


def _require_bool(obj: dict[str, Any], key: str) -> bool:
    value = obj.get(key)
    if not isinstance(value, bool):
        raise AIConfigError(f"AI config '{key}' must be a boolean")
    return value


def _require_int(obj: dict[str, Any], key: str) -> int:
    value = obj.get(key)
    if not isinstance(value, int):
        raise AIConfigError(f"AI config '{key}' must be an integer")
    return value


def _require_float(obj: dict[str, Any], key: str) -> float:
    value = obj.get(key)
    if not isinstance(value, (int, float)):
        raise AIConfigError(f"AI config '{key}' must be a number")
    return float(value)


def _require_list_of_str(obj: dict[str, Any], key: str) -> list[str]:
    value = obj.get(key)
    if not isinstance(value, list) or not value:
        raise AIConfigError(f"AI config '{key}' must be a non-empty list")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise AIConfigError(f"AI config '{key}' must be a list of non-empty strings")
    return value


def _require_dict_str_str(obj: dict[str, Any], key: str) -> dict[str, str]:
    value = obj.get(key)
    if not isinstance(value, dict) or not value:
        raise AIConfigError(f"AI config '{key}' must be a non-empty mapping")
    prompts: dict[str, str] = {}
    for k, v in value.items():
        if not isinstance(k, str) or not k.strip() or not isinstance(v, str) or not v.strip():
            raise AIConfigError(f"AI config '{key}' must map non-empty strings to non-empty strings")
        prompts[k] = v
    return prompts

