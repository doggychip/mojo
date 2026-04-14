"""LLM wrapper for OpenRouter and Anthropic API."""

import json
import os
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

DEFAULT_OPENROUTER_MODEL = "anthropic/claude-sonnet-4-20250514"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-20250514"


class LLM:
    """Unified LLM client supporting OpenRouter and Anthropic direct."""

    def __init__(self, provider: str = "openrouter", model: Optional[str] = None) -> None:
        self.provider = provider
        if provider == "anthropic":
            self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
            self.model = model or DEFAULT_ANTHROPIC_MODEL
        else:
            self.api_key = os.getenv("OPENROUTER_API_KEY", "")
            self.model = model or DEFAULT_OPENROUTER_MODEL

        if not self.api_key:
            alt_provider = "anthropic" if provider == "openrouter" else "openrouter"
            alt_key_name = "ANTHROPIC_API_KEY" if alt_provider == "anthropic" else "OPENROUTER_API_KEY"
            alt_key = os.getenv(alt_key_name, "")
            if alt_key:
                self.provider = alt_provider
                self.api_key = alt_key
                if alt_provider == "anthropic":
                    self.model = model or DEFAULT_ANTHROPIC_MODEL
                else:
                    self.model = model or DEFAULT_OPENROUTER_MODEL

    def call(self, system_prompt: str, user_message: str, temperature: float = 0.7) -> str:
        """Make an LLM call and return the response text."""
        try:
            if self.provider == "anthropic":
                return self._call_anthropic(system_prompt, user_message, temperature)
            return self._call_openrouter(system_prompt, user_message, temperature)
        except Exception as e:
            return f"[LLM Error] {e}"

    def call_json(self, system_prompt: str, user_message: str, temperature: float = 0.3) -> dict:
        """Make an LLM call expecting JSON output. Returns parsed dict or error dict."""
        raw = self.call(system_prompt, user_message, temperature)
        try:
            # Try to extract JSON from response (handles markdown code blocks)
            text = raw.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                lines = lines[1:]  # skip ```json
                end = next((i for i, l in enumerate(lines) if l.strip() == "```"), len(lines))
                text = "\n".join(lines[:end])
            return json.loads(text)
        except (json.JSONDecodeError, StopIteration):
            return {"error": "Failed to parse JSON", "raw": raw}

    def _call_openrouter(self, system_prompt: str, user_message: str, temperature: float) -> str:
        resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _call_anthropic(self, system_prompt: str, user_message: str, temperature: float) -> str:
        resp = requests.post(
            ANTHROPIC_URL,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": 4096,
                "temperature": temperature,
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": user_message},
                ],
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]
