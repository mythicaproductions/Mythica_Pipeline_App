"""Provider interface — one contract, many image generators behind it.

Each generator (OpenAI, and later Stability/Flux/etc.) implements this so the
MCP tools never need to know which engine they're talking to. See CLAUDE.md §3.1.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class ImageProvider(ABC):
    name: str = "base"

    @abstractmethod
    def generate(self, prompt: str, size: str) -> bytes:
        """Return raw image bytes (PNG) for the given prompt."""
        raise NotImplementedError
