"""Impartial LLM judge — scores agent output 0.0 to 1.0."""

from typing import Dict

from .llm import LLM
from .models import Task
from .prompts import JUDGE_SCORING_PROMPT


class Judge:
    """Evaluates agent outputs for quality."""

    def __init__(self, llm: LLM) -> None:
        self.llm = llm

    def score(self, task: Task, output: str) -> Dict:
        """Score an agent's output. Returns {"score": float, "feedback": str}."""
        user_message = (
            f"TASK: {task.description}\n"
            f"GOAL: {task.goal}\n"
            f"CONTEXT: {task.context}\n\n"
            f"AGENT OUTPUT:\n{output}"
        )
        result = self.llm.call_json(JUDGE_SCORING_PROMPT, user_message)
        if "error" in result:
            return {"score": 0.5, "feedback": f"Judge parse error: {result.get('raw', '')[:200]}"}
        score = float(result.get("score", 0.5))
        score = max(0.0, min(1.0, score))
        return {
            "score": score,
            "feedback": result.get("feedback", "No feedback provided."),
        }
