"""Three Realms (三界): 研发 / 执行 / 中枢."""

from typing import Dict, List

from .memory import Memory
from .models import AgentState, Task

REALM_CONFIG: Dict[str, Dict] = {
    "research": {
        "name_zh": "研发",
        "description": "Long-horizon, experimental, low tax",
        "tax_rate": 0.05,
        "authority": 1,
    },
    "execution": {
        "name_zh": "执行",
        "description": "Standard tasks, moderate tax",
        "tax_rate": 0.10,
        "authority": 2,
    },
    "nexus": {
        "name_zh": "中枢",
        "description": "Strategic coordination, highest tax, highest authority",
        "tax_rate": 0.15,
        "authority": 3,
    },
}


class RealmRouter:
    """Routes tasks to appropriate realms and manages realm-based operations."""

    def __init__(self, memory: Memory) -> None:
        self.memory = memory

    def route_task(self, task: Task) -> str:
        """Determine which realm a task belongs to based on its declared realm."""
        if task.realm in REALM_CONFIG:
            return task.realm
        # Fallback heuristic
        desc = task.description.lower()
        if any(w in desc for w in ["research", "analyze", "investigate", "explore", "study"]):
            return "research"
        if any(w in desc for w in ["strategy", "coordinate", "plan", "govern", "allocate"]):
            return "nexus"
        return "execution"

    def get_realm_agents(self, realm: str) -> List[AgentState]:
        """Get all alive agents in a realm."""
        return self.memory.list_alive_agents(realm=realm)

    def get_realm_stats(self) -> Dict[str, Dict]:
        """Get stats for each realm."""
        stats = {}
        for realm_name, config in REALM_CONFIG.items():
            agents = self.memory.list_alive_agents(realm=realm_name)
            stats[realm_name] = {
                **config,
                "agent_count": len(agents),
                "avg_score": (
                    sum(a.average_score for a in agents) / len(agents) if agents else 0.0
                ),
            }
        return stats
