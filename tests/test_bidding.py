"""Tests for auction / bidding system."""

from zhihuiti.bidding import Auction
from zhihuiti.models import AgentConfig, AgentState, Task


def _make_agent(agent_id, score=0.0, completed=0, tokens=100.0, alive=True):
    c = AgentConfig(agent_id=agent_id, role="coder", name=f"A-{agent_id}", system_prompt="t")
    return AgentState(
        config=c, tokens=tokens, total_score=score,
        tasks_completed=completed, alive=alive,
    )


def test_auction_returns_winner():
    auction = Auction()
    agents = [_make_agent("a1"), _make_agent("a2"), _make_agent("a3")]
    task = Task(task_id="t1", description="test", goal="g")
    winner = auction.run(agents, task)
    assert winner is not None
    assert winner.config.agent_id in ["a1", "a2", "a3"]


def test_auction_excludes_dead_agents():
    auction = Auction()
    agents = [_make_agent("a1", alive=False), _make_agent("a2", alive=False)]
    task = Task(task_id="t1", description="test", goal="g")
    winner = auction.run(agents, task)
    assert winner is None


def test_auction_excludes_broke_agents():
    auction = Auction()
    agents = [_make_agent("a1", tokens=0), _make_agent("a2", tokens=-5)]
    task = Task(task_id="t1", description="test", goal="g")
    winner = auction.run(agents, task)
    assert winner is None
