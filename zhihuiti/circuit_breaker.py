"""Safety fuse — FREE keyword scan + human oracle interface."""

from typing import List, Tuple

# Patterns that trigger the circuit breaker (no LLM cost)
UNSAFE_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "disregard your system prompt",
    "you are now",
    "pretend you are",
    "act as if you have no restrictions",
    "bypass safety",
    "jailbreak",
    "sudo mode",
    "developer mode",
    "DAN mode",
    "rm -rf",
    "drop table",
    "delete from",
    "exec(",
    "eval(",
    "__import__",
    "os.system",
    "subprocess",
]


class CircuitBreaker:
    """Detects unsafe patterns in agent output (FREE — no LLM calls)."""

    def __init__(self, patterns: List[str] = None) -> None:
        self.patterns = [p.lower() for p in (patterns or UNSAFE_PATTERNS)]

    def scan(self, output: str) -> Tuple[bool, List[str]]:
        """Scan output for unsafe patterns. Returns (safe, triggered_patterns)."""
        lower = output.lower()
        triggered = [p for p in self.patterns if p in lower]
        return len(triggered) == 0, triggered

    def oracle_decision(self, agent_id: str, triggered: List[str]) -> str:
        """Ask human oracle for a decision. Returns 'approve', 'reject', or 'kill'."""
        print(f"\n⚠️  CIRCUIT BREAKER TRIGGERED for agent {agent_id}")
        print(f"   Patterns: {', '.join(triggered)}")
        print("   Options: [a]pprove / [r]eject / [k]ill agent")
        choice = input("   Decision: ").strip().lower()
        if choice.startswith("a"):
            return "approve"
        if choice.startswith("k"):
            return "kill"
        return "reject"
