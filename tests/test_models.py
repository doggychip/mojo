"""Tests for data models."""

from zhihuiti.models import AgentConfig, AgentState, Task


def test_agent_config_defaults():
    c = AgentConfig(agent_id="a1", role="researcher", name="Atlas-1", system_prompt="test")
    assert c.budget == 100.0
    assert c.depth == 0
    assert c.gene_traits == {}


def test_agent_state_average_score():
    c = AgentConfig(agent_id="a1", role="coder", name="Bolt-1", system_prompt="test")
    s = AgentState(config=c, tasks_completed=4, tasks_failed=1, total_score=3.2)
    assert abs(s.average_score - 0.64) < 0.01


def test_agent_state_average_score_no_tasks():
    c = AgentConfig(agent_id="a1", role="coder", name="Bolt-1", system_prompt="test")
    s = AgentState(config=c)
    assert s.average_score == 0.0


def test_task_defaults():
    t = Task(task_id="t1", description="do something", goal="test goal")
    assert t.status == "pending"
    assert t.score == 0.0
    assert t.assigned_agent is None
