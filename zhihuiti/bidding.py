"""Competitive auction system — lowest qualified bid wins."""

import random
from typing import List, Optional, Tuple

from .models import AgentState, Task


class Auction:
    """Runs competitive bidding for task assignment."""

    MIN_CONFIDENCE = 0.5

    def run(self, agents: List[AgentState], task: Task) -> Optional[AgentState]:
        """Run an auction among agents. Returns the winning agent or None."""
        bids = self._collect_bids(agents, task)
        if not bids:
            return None
        # Sort by cost ascending, then by historical score descending for tiebreak
        bids.sort(key=lambda b: (b[1], -b[0].average_score))
        return bids[0][0]

    def _collect_bids(self, agents: List[AgentState], task: Task) -> List[Tuple[AgentState, float, float]]:
        """Collect (agent, cost, confidence) bids from eligible agents."""
        bids = []
        for agent in agents:
            if not agent.alive or agent.tokens <= 0:
                continue
            cost, confidence = self._generate_bid(agent, task)
            if confidence >= self.MIN_CONFIDENCE:
                bids.append((agent, cost, confidence))
        return bids

    def _generate_bid(self, agent: AgentState, task: Task) -> Tuple[float, float]:
        """Generate a bid for an agent. Returns (cost, confidence).

        Cost is based on agent's budget expectations + noise.
        Confidence is based on role match and past performance.
        """
        # Base cost: agents with higher scores bid more confidently (lower cost)
        base_cost = 20.0
        score_discount = agent.average_score * 10.0
        noise = random.uniform(-3.0, 3.0)
        cost = max(5.0, base_cost - score_discount + noise)

        # Confidence: higher for agents with good track records
        base_confidence = 0.6
        if agent.tasks_completed > 0:
            base_confidence = 0.5 + agent.average_score * 0.4
        confidence = min(1.0, base_confidence + random.uniform(-0.1, 0.1))

        return cost, confidence
