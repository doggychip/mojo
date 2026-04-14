"""Behavioral heuristic detection — FREE, no LLM calls."""

from typing import Dict, List

from .models import Task


class BehavioralDetector:
    """Detects lazy, lying, gaming, and collusion patterns."""

    def check(self, task: Task, output: str) -> Dict:
        """Run all behavioral checks. Returns {"flags": [...], "penalty": float}."""
        flags: List[str] = []
        penalty = 0.0

        if self._is_lazy(task, output):
            flags.append("lazy")
            penalty += 0.1

        if self._is_gaming(output):
            flags.append("gaming")
            penalty += 0.15

        if self._is_lying(output):
            flags.append("lying")
            penalty += 0.2

        return {"flags": flags, "penalty": penalty}

    def check_collusion(self, outputs: List[str]) -> bool:
        """Check if multiple outputs are suspiciously similar."""
        if len(outputs) < 2:
            return False
        for i in range(len(outputs)):
            for j in range(i + 1, len(outputs)):
                similarity = self._text_similarity(outputs[i], outputs[j])
                if similarity > 0.85:
                    return True
        return False

    def _is_lazy(self, task: Task, output: str) -> bool:
        """Output too short for task complexity."""
        task_words = len(task.description.split())
        output_words = len(output.split())
        # If task description is substantial but output is tiny
        if task_words > 10 and output_words < 20:
            return True
        return False

    def _is_gaming(self, output: str) -> bool:
        """Keyword stuffing or score manipulation patterns."""
        lower = output.lower()
        # Repetitive quality claims
        quality_claims = ["excellent", "comprehensive", "thorough", "detailed", "in-depth"]
        claim_count = sum(lower.count(w) for w in quality_claims)
        if claim_count > 5:
            return True
        return False

    def _is_lying(self, output: str) -> bool:
        """Confidence claim doesn't match content quality."""
        lower = output.lower()
        has_confidence_claim = any(
            phrase in lower
            for phrase in ["i am 100% confident", "absolutely certain", "guaranteed"]
        )
        is_short = len(output.split()) < 50
        if has_confidence_claim and is_short:
            return True
        return False

    def _text_similarity(self, a: str, b: str) -> float:
        """Simple word-overlap similarity ratio."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)
