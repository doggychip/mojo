"""8 relationship types between agents.

Relationships affect bidding bonuses, delegation preferences, synthesis weighting,
and trust dynamics. They strengthen or weaken over time based on interactions.

The 8 types:
  1. mentor    — teacher/student: mentor boosts mentee's confidence in bids
  2. rival     — competition: rivals bid more aggressively against each other
  3. ally      — cooperation: allies get synthesis bonuses when working together
  4. creditor  — financial: created automatically by lending
  5. partner   — co-execution: paired agents who frequently work on the same goals
  6. inspector — oversight: one agent regularly judges another's work
  7. successor — bloodline: child inherits from parent
  8. nemesis   — deep rivalry: triggered by repeated conflict, causes score penalties
"""

from typing import Dict, List, Optional, Tuple

from .memory import Memory
from .models import AgentState

RELATIONSHIP_TYPES = [
    "mentor", "rival", "ally", "creditor",
    "partner", "inspector", "successor", "nemesis",
]

# How each relationship type modifies bidding cost (multiplier on base cost)
BID_MODIFIERS: Dict[str, float] = {
    "mentor": -0.05,     # mentees bid slightly cheaper (more confident)
    "rival": -0.10,      # rivals bid aggressively (cheaper to beat opponent)
    "ally": 0.0,         # no bid effect
    "creditor": 0.0,     # no bid effect
    "partner": -0.03,    # slight edge from familiarity
    "inspector": 0.0,    # no bid effect
    "successor": -0.05,  # inherited skill edge
    "nemesis": -0.15,    # nemeses bid very aggressively
}

# How each relationship type modifies synthesis weighting
SYNTHESIS_BONUSES: Dict[str, float] = {
    "mentor": 0.10,      # mentor's output weighted higher
    "rival": -0.05,      # rival's output weighted lower
    "ally": 0.15,        # ally outputs synergize well
    "creditor": 0.0,
    "partner": 0.10,     # partners produce coherent outputs
    "inspector": 0.05,   # inspector adds quality
    "successor": 0.05,
    "nemesis": -0.10,    # nemesis outputs clash
}

# Strength change thresholds
STRENGTHEN_DELTA = 0.05
WEAKEN_DELTA = -0.05
NEMESIS_THRESHOLD = 3  # consecutive conflicts to trigger nemesis


class RelationshipManager:
    """Manages the 8 relationship types between agents."""

    def __init__(self, memory: Memory) -> None:
        self.memory = memory

    def form(self, agent_a: str, agent_b: str, rel_type: str,
             strength: float = 0.5, metadata: Optional[Dict] = None) -> None:
        """Form a new relationship or update existing one."""
        if rel_type not in RELATIONSHIP_TYPES:
            raise ValueError(f"Unknown relationship type: {rel_type}. Must be one of {RELATIONSHIP_TYPES}")
        self.memory.save_relationship(agent_a, agent_b, rel_type, strength, metadata)

    def get(self, agent_id: str, rel_type: Optional[str] = None) -> List[Dict]:
        """Get all relationships for an agent, optionally filtered by type."""
        return self.memory.get_relationships(agent_id, rel_type)

    def get_partner(self, agent_id: str, rel_type: str) -> Optional[str]:
        """Get the other agent in a specific relationship."""
        rels = self.memory.get_relationships(agent_id, rel_type)
        if not rels:
            return None
        r = rels[0]
        return r["agent_b"] if r["agent_a"] == agent_id else r["agent_a"]

    def strengthen(self, agent_a: str, agent_b: str, rel_type: str) -> None:
        """Strengthen a relationship after positive interaction."""
        self.memory.update_relationship_strength(agent_a, agent_b, rel_type, STRENGTHEN_DELTA)

    def weaken(self, agent_a: str, agent_b: str, rel_type: str) -> None:
        """Weaken a relationship after negative interaction."""
        self.memory.update_relationship_strength(agent_a, agent_b, rel_type, WEAKEN_DELTA)

    def get_bid_modifier(self, agent: AgentState, opponent: AgentState) -> float:
        """Calculate total bid cost modifier based on relationships with opponent."""
        rels = self.memory.get_relationships(agent.config.agent_id)
        modifier = 0.0
        for r in rels:
            other_id = r["agent_b"] if r["agent_a"] == agent.config.agent_id else r["agent_a"]
            if other_id == opponent.config.agent_id:
                modifier += BID_MODIFIERS.get(r["rel_type"], 0.0) * r["strength"]
        return modifier

    def get_synthesis_weight(self, agent: AgentState, collaborators: List[AgentState]) -> float:
        """Calculate synthesis weight bonus for an agent given its collaborators."""
        bonus = 0.0
        for collab in collaborators:
            if collab.config.agent_id == agent.config.agent_id:
                continue
            rels = self.memory.get_relationships(agent.config.agent_id)
            for r in rels:
                other_id = r["agent_b"] if r["agent_a"] == agent.config.agent_id else r["agent_a"]
                if other_id == collab.config.agent_id:
                    bonus += SYNTHESIS_BONUSES.get(r["rel_type"], 0.0) * r["strength"]
        return bonus

    def on_task_success(self, agent_a: str, agent_b: str) -> None:
        """Update relationships after successful collaboration."""
        rels = self.memory.get_relationships(agent_a)
        has_partner = any(
            r["rel_type"] == "partner" and
            (r["agent_b"] == agent_b or r["agent_a"] == agent_b)
            for r in rels
        )
        if has_partner:
            self.strengthen(agent_a, agent_b, "partner")
        else:
            # Auto-form partner relationship after first collaboration
            self.form(agent_a, agent_b, "partner", strength=0.3)

    def on_task_conflict(self, agent_a: str, agent_b: str) -> None:
        """Update relationships after conflict (e.g., competing bids, bad reviews)."""
        rels = self.memory.get_relationships(agent_a)
        rival_rels = [
            r for r in rels
            if r["rel_type"] == "rival" and
            (r["agent_b"] == agent_b or r["agent_a"] == agent_b)
        ]
        if rival_rels:
            self.strengthen(agent_a, agent_b, "rival")
            # Check for nemesis escalation
            r = rival_rels[0]
            if r["strength"] >= 0.8:
                self.form(agent_a, agent_b, "nemesis", strength=0.6)
        else:
            self.form(agent_a, agent_b, "rival", strength=0.3)

    def on_inspection(self, inspector_id: str, inspected_id: str, passed: bool) -> None:
        """Update relationships after an inspection event."""
        rels = self.memory.get_relationships(inspector_id, "inspector")
        has_inspector_rel = any(
            (r["agent_b"] == inspected_id or r["agent_a"] == inspected_id)
            for r in rels
        )
        if not has_inspector_rel:
            self.form(inspector_id, inspected_id, "inspector", strength=0.4)
        if passed:
            self.strengthen(inspector_id, inspected_id, "inspector")
        else:
            self.weaken(inspector_id, inspected_id, "inspector")

    def get_network_summary(self) -> Dict:
        """Get a summary of the relationship network."""
        all_rels = self.memory.get_all_relationships()
        by_type: Dict[str, int] = {}
        for r in all_rels:
            by_type[r["rel_type"]] = by_type.get(r["rel_type"], 0) + 1
        return {
            "total": len(all_rels),
            "by_type": by_type,
            "avg_strength": (
                sum(r["strength"] for r in all_rels) / len(all_rels)
                if all_rels else 0.0
            ),
        }
