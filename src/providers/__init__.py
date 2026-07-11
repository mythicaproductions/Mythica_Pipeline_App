"""Provider registry. Add a new generator by appending its adapter here."""
from __future__ import annotations

from providers.base import ImageProvider
from providers.openai_provider import OpenAIProvider

_PROVIDERS: dict[str, ImageProvider] = {p.name: p for p in [OpenAIProvider()]}


def get_provider(name: str) -> ImageProvider:
    try:
        return _PROVIDERS[name]
    except KeyError:
        raise ValueError(
            f"Unknown provider '{name}'. Available: {sorted(_PROVIDERS)}"
        )


def available_providers() -> list[str]:
    return sorted(_PROVIDERS)
