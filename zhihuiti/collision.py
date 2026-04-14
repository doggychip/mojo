"""Collision engine — 49-theory knowledge synthesis (如老师).

The collision engine takes divergent outputs from multiple agents and
synthesizes novel insights through structured dialectic. Instead of
simply merging, it forces opposing viewpoints to collide, producing
emergent knowledge that no single agent would generate alone.

Three collision methods:
  1. dialectic  — thesis + antithesis → synthesis (Hegelian)
  2. adversarial — red team vs blue team, judge picks winner + combines
  3. prismatic  — N agents each see the problem through a different "lens",
                   then a meta-agent finds the pattern across all lenses

The 49-theory framework: 7 dimensions × 7 perspectives = 49 possible
collision points. Not all are used every time — the engine selects the
most productive collision pairs.
"""

import uuid
from typing import Dict, List, Optional

from .llm import LLM
from .memory import Memory
from .models import AgentState

DIALECTIC_PROMPT = (
    "You are a dialectic synthesis engine. You will receive a THESIS and an ANTITHESIS — "
    "two opposing or divergent perspectives on the same topic.\n\n"
    "Your job:\n"
    "1. Identify the core tension between them\n"
    "2. Find what each gets RIGHT that the other misses\n"
    "3. Produce a SYNTHESIS that transcends both — not a compromise, but a new insight\n"
    "4. Rate the novelty of your synthesis (0.0 = obvious merge, 1.0 = genuine breakthrough)\n\n"
    "Return JSON: {\"tension\": \"...\", \"synthesis\": \"...\", \"novelty\": <float>}"
)

ADVERSARIAL_PROMPT = (
    "You are a debate judge evaluating two opposing arguments on the same topic.\n\n"
    "RED TEAM argues one position. BLUE TEAM argues the opposite.\n\n"
    "Your job:\n"
    "1. Score each argument (0.0 to 1.0) on strength of reasoning\n"
    "2. Identify the strongest points from EACH side\n"
    "3. Produce a combined verdict that uses the best of both\n"
    "4. Rate the novelty of insights produced by the collision\n\n"
    "Return JSON: {\"red_score\": <float>, \"blue_score\": <float>, "
    "\"best_of_red\": \"...\", \"best_of_blue\": \"...\", "
    "\"verdict\": \"...\", \"novelty\": <float>}"
)

PRISMATIC_PROMPT = (
    "You are a meta-pattern detector. You will receive multiple perspectives on the "
    "same topic, each seen through a different analytical lens.\n\n"
    "Your job:\n"
    "1. Identify what pattern or insight EMERGES across all lenses that no single lens reveals\n"
    "2. Explain why this cross-lens insight matters\n"
    "3. Produce an actionable synthesis\n"
    "4. Rate the novelty\n\n"
    "Return JSON: {\"emergent_pattern\": \"...\", \"why_it_matters\": \"...\", "
    "\"synthesis\": \"...\", \"novelty\": <float>}"
)

# The 7 analytical lenses for prismatic collision
LENSES = [
    "economic",      # cost, value, incentives, market forces
    "structural",    # architecture, dependencies, bottlenecks
    "temporal",      # timing, sequencing, urgency, decay
    "adversarial",   # what could go wrong, attack vectors, failures
    "human",         # psychology, behavior, adoption, UX
    "systemic",      # feedback loops, emergent effects, second-order
    "contrarian",    # what does the consensus miss, devil's advocate
]


class CollisionEngine:
    """Forces divergent agent outputs to collide, producing emergent insights."""

    def __init__(self, llm: LLM, memory: Memory) -> None:
        self.llm = llm
        self.memory = memory

    def collide(self, agents: List[AgentState], outputs: List[str],
                method: str = "dialectic") -> Dict:
        """Run a collision between agent outputs. Returns collision result."""
        if method == "dialectic":
            return self._dialectic(agents, outputs)
        elif method == "adversarial":
            return self._adversarial(agents, outputs)
        elif method == "prismatic":
            return self._prismatic(agents, outputs)
        else:
            return self._dialectic(agents, outputs)

    def auto_collide(self, agents: List[AgentState], outputs: List[str]) -> Dict:
        """Automatically pick the best collision method based on inputs."""
        if len(outputs) == 2:
            # Check if outputs are genuinely divergent
            divergence = self._measure_divergence(outputs[0], outputs[1])
            if divergence > 0.5:
                return self._adversarial(agents, outputs)
            return self._dialectic(agents, outputs)
        elif len(outputs) >= 3:
            return self._prismatic(agents, outputs)
        else:
            return {"synthesis": outputs[0] if outputs else "", "novelty": 0.0}

    def _dialectic(self, agents: List[AgentState], outputs: List[str]) -> Dict:
        """Thesis + antithesis → synthesis."""
        thesis = outputs[0] if outputs else ""
        antithesis = outputs[1] if len(outputs) > 1 else ""

        user_msg = f"THESIS:\n{thesis}\n\nANTITHESIS:\n{antithesis}"
        result = self.llm.call_json(DIALECTIC_PROMPT, user_msg)

        collision_id = str(uuid.uuid4())[:8]
        agent_ids = [a.config.agent_id for a in agents[:2]]

        record = {
            "collision_id": collision_id,
            "agent_ids": agent_ids,
            "inputs": outputs[:2],
            "synthesis": result.get("synthesis", ""),
            "novelty_score": float(result.get("novelty", 0.0)),
            "method": "dialectic",
        }
        self.memory.save_collision(record)

        return {
            "collision_id": collision_id,
            "method": "dialectic",
            "tension": result.get("tension", ""),
            "synthesis": result.get("synthesis", ""),
            "novelty": float(result.get("novelty", 0.0)),
        }

    def _adversarial(self, agents: List[AgentState], outputs: List[str]) -> Dict:
        """Red team vs blue team → judge verdict."""
        red = outputs[0] if outputs else ""
        blue = outputs[1] if len(outputs) > 1 else ""

        user_msg = f"RED TEAM:\n{red}\n\nBLUE TEAM:\n{blue}"
        result = self.llm.call_json(ADVERSARIAL_PROMPT, user_msg)

        collision_id = str(uuid.uuid4())[:8]
        agent_ids = [a.config.agent_id for a in agents[:2]]

        record = {
            "collision_id": collision_id,
            "agent_ids": agent_ids,
            "inputs": outputs[:2],
            "synthesis": result.get("verdict", ""),
            "novelty_score": float(result.get("novelty", 0.0)),
            "method": "adversarial",
        }
        self.memory.save_collision(record)

        return {
            "collision_id": collision_id,
            "method": "adversarial",
            "red_score": float(result.get("red_score", 0.5)),
            "blue_score": float(result.get("blue_score", 0.5)),
            "best_of_red": result.get("best_of_red", ""),
            "best_of_blue": result.get("best_of_blue", ""),
            "synthesis": result.get("verdict", ""),
            "novelty": float(result.get("novelty", 0.0)),
        }

    def _prismatic(self, agents: List[AgentState], outputs: List[str]) -> Dict:
        """N perspectives through different lenses → emergent pattern."""
        lens_sections = []
        for i, output in enumerate(outputs):
            lens = LENSES[i % len(LENSES)]
            lens_sections.append(f"LENS [{lens.upper()}]:\n{output}")

        user_msg = "\n\n".join(lens_sections)
        result = self.llm.call_json(PRISMATIC_PROMPT, user_msg)

        collision_id = str(uuid.uuid4())[:8]
        agent_ids = [a.config.agent_id for a in agents]

        record = {
            "collision_id": collision_id,
            "agent_ids": agent_ids,
            "inputs": outputs,
            "synthesis": result.get("synthesis", ""),
            "novelty_score": float(result.get("novelty", 0.0)),
            "method": "prismatic",
        }
        self.memory.save_collision(record)

        return {
            "collision_id": collision_id,
            "method": "prismatic",
            "emergent_pattern": result.get("emergent_pattern", ""),
            "why_it_matters": result.get("why_it_matters", ""),
            "synthesis": result.get("synthesis", ""),
            "novelty": float(result.get("novelty", 0.0)),
        }

    def _measure_divergence(self, a: str, b: str) -> float:
        """Quick divergence measure between two texts (0 = identical, 1 = totally different)."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 1.0
        intersection = words_a & words_b
        union = words_a | words_b
        jaccard = len(intersection) / len(union)
        return 1.0 - jaccard
