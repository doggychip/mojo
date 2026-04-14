"""Tests for AgentManager."""

from zhihuiti.agents import AgentManager


def test_spawn(memory, mock_llm):
    mgr = AgentManager(mock_llm, memory)
    agent = mgr.spawn("researcher", realm="research")

    assert agent.config.role == "researcher"
    assert agent.realm == "research"
    assert agent.alive is True
    assert agent.tokens == 100.0

    # Persisted
    loaded = memory.load_agent(agent.config.agent_id)
    assert loaded is not None


def test_execute(memory, mock_llm):
    from zhihuiti.models import Task
    mgr = AgentManager(mock_llm, memory)
    agent = mgr.spawn("coder")
    task = Task(task_id="t1", description="write hello world", goal="test")
    result = mgr.execute(agent, task)
    assert isinstance(result, str)
    assert len(result) > 0
    assert len(mock_llm.call_log) == 1


def test_cull(memory, mock_llm):
    mgr = AgentManager(mock_llm, memory)
    agent = mgr.spawn("coder")
    agent.tasks_completed = 2
    agent.tasks_failed = 2
    agent.total_score = 0.8  # avg = 0.2 < 0.3 threshold

    assert mgr.check_cull(agent) is True
    assert agent.alive is False


def test_no_cull_too_few_tasks(memory, mock_llm):
    mgr = AgentManager(mock_llm, memory)
    agent = mgr.spawn("coder")
    agent.tasks_completed = 1
    agent.tasks_failed = 0
    agent.total_score = 0.1  # low but only 1 task

    assert mgr.check_cull(agent) is False
    assert agent.alive is True


def test_promote(memory, mock_llm):
    mgr = AgentManager(mock_llm, memory)
    agent = mgr.spawn("researcher", realm="execution")
    agent.tasks_completed = 6
    agent.total_score = 5.4  # avg = 0.9 > 0.8

    new_realm = mgr.check_promote(agent)
    assert new_realm == "research"
    assert agent.realm == "research"


def test_ensure_agents_for_realm(memory, mock_llm):
    mgr = AgentManager(mock_llm, memory)
    agents = mgr.ensure_agents_for_realm("execution", min_count=3)
    assert len(agents) == 3
    for a in agents:
        assert a.realm == "execution"


def test_synthesize(memory, mock_llm):
    mgr = AgentManager(mock_llm, memory)

    # Single result returns as-is
    assert mgr.synthesize(["only one"]) == "only one"

    # Multiple results calls LLM
    result = mgr.synthesize(["result A", "result B"])
    assert isinstance(result, str)
    assert len(mock_llm.call_log) == 1
