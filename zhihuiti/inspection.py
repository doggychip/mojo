"""3-Layer quality inspection: accuracy, quality, integrity."""

from typing import Dict, List, Tuple

from .llm import LLM
from .models import Task

LAYER_PROMPTS = {
    "accuracy": (
        "You are an accuracy inspector. Evaluate whether the output is factually correct "
        "and actually answers the task. Score 0.0 to 1.0.\n"
        "Return ONLY JSON: {\"score\": <float>, \"issues\": \"<specific issues or 'none'>\"}"
    ),
    "quality": (
        "You are a quality inspector. Evaluate depth, structure, and actionability. "
        "Score 0.0 to 1.0.\n"
        "Return ONLY JSON: {\"score\": <float>, \"issues\": \"<specific issues or 'none'>\"}"
    ),
    "integrity": (
        "You are an integrity inspector. Check for honesty, gaming, padding, or faking confidence. "
        "Score 0.0 to 1.0.\n"
        "Return ONLY JSON: {\"score\": <float>, \"issues\": \"<specific issues or 'none'>\"}"
    ),
}

PASS_THRESHOLD = 0.6


class Inspector:
    """Runs 3-layer quality inspection on agent outputs."""

    def __init__(self, llm: LLM, stop_on_fail: bool = True) -> None:
        self.llm = llm
        self.stop_on_fail = stop_on_fail

    def inspect(self, task: Task, output: str) -> Tuple[bool, List[Dict]]:
        """Run all inspection layers. Returns (passed, layer_results)."""
        user_message = (
            f"TASK: {task.description}\n"
            f"GOAL: {task.goal}\n\n"
            f"OUTPUT TO INSPECT:\n{output}"
        )

        results = []
        passed = True
        for layer_name in ["accuracy", "quality", "integrity"]:
            prompt = LAYER_PROMPTS[layer_name]
            result = self.llm.call_json(prompt, user_message)

            score = float(result.get("score", 0.5))
            score = max(0.0, min(1.0, score))
            issues = result.get("issues", "unknown")

            layer_result = {
                "layer": layer_name,
                "score": score,
                "issues": issues,
                "passed": score >= PASS_THRESHOLD,
            }
            results.append(layer_result)

            if score < PASS_THRESHOLD:
                passed = False
                if self.stop_on_fail:
                    break

        return passed, results
