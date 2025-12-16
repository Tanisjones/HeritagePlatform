from __future__ import annotations

import os
from dataclasses import dataclass
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
    base_url = _require_str(ai, "base_url")
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
    )


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

