"""Data models for zhihuiti agents, tasks, and state."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class AgentConfig:
    """Configuration for spawning an agent."""

    agent_id: str
    role: str  # researcher, analyst, coder, writer, architect, trader, strategist, judge, auditor, governor
    name: str
    system_prompt: str
    budget: float = 100.0
    depth: int = 0  # sub-agent depth (max 3)
    gene_traits: Dict = field(default_factory=dict)


@dataclass
class Task:
    """A unit of work to be executed by an agent."""

    task_id: str
    description: str
    goal: str
    context: str = ""
    assigned_agent: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[str] = None
    score: float = 0.0
    realm: str = "execution"  # research / execution / nexus


@dataclass
class AgentState:
    """Runtime state of a living or dead agent."""

    config: AgentConfig
    tokens: float = 100.0
    total_score: float = 0.0
    tasks_completed: int = 0
    tasks_failed: int = 0
    realm: str = "execution"
    alive: bool = True
    generation: int = 1
    parent_ids: List[str] = field(default_factory=list)

    @property
    def average_score(self) -> float:
        """Average task score, or 0.0 if no tasks completed."""
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return 0.0
        return self.total_score / total
