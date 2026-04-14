"""AgentManager — spawn, execute, delegate, synthesize, cull, promote."""

import uuid
from typing import List, Optional

from .llm import LLM
from .memory import Memory
from .models import AgentConfig, AgentState, Task
from .prompts import SYNTHESIS_PROMPT, get_role_prompt

# Name fragments for generating agent names
_PREFIXES = ["Atlas", "Nova", "Sage", "Bolt", "Vex", "Aria", "Onyx", "Pulse", "Zeta", "Flux"]
_counter = 0


def _generate_name(role: str) -> str:
    global _counter
    _counter += 1
    prefix = _PREFIXES[hash(role) % len(_PREFIXES)]
    return f"{prefix}-{_counter}"


class AgentManager:
    """Manages agent lifecycle: spawn, execute, cull, promote."""

    CULL_THRESHOLD = 0.3
    CULL_MIN_TASKS = 3
    PROMOTE_THRESHOLD = 0.8
    PROMOTE_MIN_TASKS = 5
    MAX_DEPTH = 3

    def __init__(self, llm: LLM, memory: Memory) -> None:
        self.llm = llm
        self.memory = memory

    def spawn(
        self,
        role: str,
        depth: int = 0,
        budget: float = 100.0,
        gene_traits: Optional[dict] = None,
        realm: str = "execution",
    ) -> AgentState:
        """Create a new agent and persist it."""
        agent_id = str(uuid.uuid4())[:8]
        config = AgentConfig(
            agent_id=agent_id,
            role=role,
            name=_generate_name(role),
            system_prompt=get_role_prompt(role),
            budget=budget,
            depth=depth,
            gene_traits=gene_traits or {},
        )
        state = AgentState(
            config=config,
            tokens=budget,
            realm=realm,
        )
        self.memory.save_agent(state)
        return state

    def execute(self, agent: AgentState, task: Task) -> str:
        """Have an agent execute a task via LLM call."""
        user_message = (
            f"TASK: {task.description}\n"
            f"GOAL: {task.goal}\n"
        )
        if task.context:
            user_message += f"CONTEXT: {task.context}\n"

        result = self.llm.call(agent.config.system_prompt, user_message)
        return result

    def delegate(self, agent: AgentState, task: Task) -> List[str]:
        """Delegate a task by spawning sub-agents (if depth allows)."""
        if agent.config.depth >= self.MAX_DEPTH:
            return [self.execute(agent, task)]

        # Spawn 2-3 sub-agents to handle the task in parallel
        sub_roles = self._pick_sub_roles(task)
        results = []
        for role in sub_roles:
            sub = self.spawn(
                role=role,
                depth=agent.config.depth + 1,
                budget=agent.config.budget / len(sub_roles),
                realm=agent.realm,
            )
            result = self.execute(sub, task)
            results.append(result)
        return results

    def synthesize(self, results: List[str]) -> str:
        """Merge multiple agent outputs into a single coherent result."""
        if len(results) == 1:
            return results[0]

        combined = "\n\n---\n\n".join(
            f"AGENT OUTPUT {i+1}:\n{r}" for i, r in enumerate(results)
        )
        return self.llm.call(SYNTHESIS_PROMPT, combined)

    def cull(self, agent: AgentState) -> None:
        """Kill an underperforming agent."""
        agent.alive = False
        self.memory.save_agent(agent)

    def promote(self, agent: AgentState, new_realm: str) -> None:
        """Promote an agent to a new realm."""
        agent.realm = new_realm
        self.memory.save_agent(agent)

    def check_cull(self, agent: AgentState) -> bool:
        """Check if an agent should be culled. Returns True if culled."""
        total = agent.tasks_completed + agent.tasks_failed
        if total >= self.CULL_MIN_TASKS and agent.average_score < self.CULL_THRESHOLD:
            self.cull(agent)
            return True
        return False

    def check_promote(self, agent: AgentState) -> Optional[str]:
        """Check if an agent should be promoted. Returns new realm or None."""
        if agent.tasks_completed >= self.PROMOTE_MIN_TASKS and agent.average_score > self.PROMOTE_THRESHOLD:
            if agent.realm == "execution":
                self.promote(agent, "research")
                return "research"
            elif agent.realm == "research":
                self.promote(agent, "nexus")
                return "nexus"
        return None

    def ensure_agents_for_realm(self, realm: str, min_count: int = 3) -> List[AgentState]:
        """Ensure minimum agents exist in a realm, spawning if needed."""
        existing = self.memory.list_alive_agents(realm=realm)
        if len(existing) >= min_count:
            return existing

        realm_roles = {
            "research": ["researcher", "analyst", "researcher"],
            "execution": ["coder", "writer", "analyst"],
            "nexus": ["strategist", "governor", "architect"],
        }
        roles = realm_roles.get(realm, ["researcher", "analyst", "coder"])
        for i in range(min_count - len(existing)):
            role = roles[i % len(roles)]
            agent = self.spawn(role=role, realm=realm)
            existing.append(agent)
        return existing

    def _pick_sub_roles(self, task: Task) -> List[str]:
        """Pick sub-agent roles based on task description heuristics."""
        desc = task.description.lower()
        if any(w in desc for w in ["research", "find", "search", "investigate"]):
            return ["researcher", "analyst"]
        if any(w in desc for w in ["code", "implement", "build", "script"]):
            return ["coder", "auditor"]
        if any(w in desc for w in ["write", "report", "summarize", "document"]):
            return ["writer", "analyst"]
        if any(w in desc for w in ["trade", "signal", "market", "stock"]):
            return ["trader", "analyst"]
        return ["researcher", "writer"]
