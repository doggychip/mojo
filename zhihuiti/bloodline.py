"""Bloodline system — multi-parent merge, 7-gen lineage, 诛七族."""

from typing import Dict, List, Optional

from .memory import Memory
from .models import AgentState


class Bloodline:
    """Tracks agent lineage and handles trait inheritance."""

    MAX_GENERATIONS = 7

    def __init__(self, memory: Memory) -> None:
        self.memory = memory

    def register_birth(self, child: AgentState, parents: List[AgentState]) -> None:
        """Record a new agent's lineage."""
        parent_ids = [p.config.agent_id for p in parents]
        merged = self._merge_traits(parents)
        child.config.gene_traits = merged
        child.parent_ids = parent_ids
        child.generation = max((p.generation for p in parents), default=0) + 1
        self.memory.save_bloodline(
            child.config.agent_id, parent_ids, merged, child.generation
        )
        self.memory.save_agent(child)

    def merge_on_death(self, dead_agent: AgentState, top_performers: List[AgentState]) -> Dict:
        """Merge traits from top performers when an agent dies. Returns merged traits."""
        parents = [dead_agent] + top_performers[:2]
        return self._merge_traits(parents)

    def trace_lineage(self, agent_id: str) -> List[Dict]:
        """Trace lineage back up to 7 generations."""
        return self.memory.get_lineage(agent_id, self.MAX_GENERATIONS)

    def purge_seven_clans(self, fraud_agent_id: str) -> List[str]:
        """诛七族 — penalize entire lineage on fraud detection. Returns list of penalized IDs."""
        lineage = self.trace_lineage(fraud_agent_id)
        penalized = set()
        for entry in lineage:
            penalized.add(entry["child_id"])
            for pid in entry["parent_ids"]:
                penalized.add(pid)

        for agent_id in penalized:
            agent = self.memory.load_agent(agent_id)
            if agent and agent.alive:
                agent.tokens = max(0, agent.tokens - 50)
                agent.total_score = max(0, agent.total_score - 0.5)
                self.memory.save_agent(agent)

        return list(penalized)

    def _merge_traits(self, agents: List[AgentState]) -> Dict:
        """Merge gene_traits from multiple agents, weighted by score."""
        if not agents:
            return {}
        merged: Dict = {}
        total_score = sum(max(a.average_score, 0.1) for a in agents)
        for agent in agents:
            weight = max(agent.average_score, 0.1) / total_score
            for key, value in agent.config.gene_traits.items():
                if isinstance(value, (int, float)):
                    merged[key] = merged.get(key, 0.0) + value * weight
                else:
                    # For non-numeric traits, keep the one from the highest scorer
                    if key not in merged:
                        merged[key] = value
        return merged
