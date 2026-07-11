"""OpenAI image provider — a thin adapter over the EXISTING service.

This reuses src/services/openai_service.py as-is (no duplication). The only
difference from the desktop app is where the API key comes from: the server
reads it from the OPENAI_API_KEY environment variable instead of the macOS
keychain (a cloud host has no keychain). See CLAUDE.md §5.
"""
from __future__ import annotations

import os

from providers.base import ImageProvider
from services import openai_service


class OpenAIProvider(ImageProvider):
    name = "openai"

    def generate(self, prompt: str, size: str) -> bytes:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set in the environment")
        return openai_service.generate_image(api_key, prompt, size)
