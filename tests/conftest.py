"""Shared test fixtures for zhihuiti."""

import json
import os
import tempfile

import pytest

from zhihuiti.llm import LLM
from zhihuiti.memory import Memory


class MockLLM(LLM):
    """LLM mock that returns canned responses without making API calls."""

    def __init__(self, responses=None):
        self.provider = "mock"
        self.api_key = "mock"
        self.model = "mock"
        self.responses = responses or []
        self.call_log = []
        self._call_index = 0

    def call(self, system_prompt: str, user_message: str, temperature: float = 0.7) -> str:
        self.call_log.append({
            "system_prompt": system_prompt,
            "user_message": user_message,
            "temperature": temperature,
        })
        if self._call_index < len(self.responses):
            resp = self.responses[self._call_index]
            self._call_index += 1
            return resp
        return "Mock LLM response: task completed successfully with detailed analysis."

    def call_json(self, system_prompt: str, user_message: str, temperature: float = 0.3) -> dict:
        raw = self.call(system_prompt, user_message, temperature)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"score": 0.75, "feedback": "Mock judge feedback"}


@pytest.fixture
def mock_llm():
    return MockLLM()


@pytest.fixture
def memory():
    """Fresh in-memory-like SQLite database for each test."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    mem = Memory(tmp.name)
    yield mem
    mem.close()
    os.unlink(tmp.name)
