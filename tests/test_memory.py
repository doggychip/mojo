"""Tests for SQLite persistence layer."""

from zhihuiti.models import AgentConfig, AgentState, Task


def test_save_and_load_agent(memory):
    c = AgentConfig(agent_id="a1", role="researcher", name="Atlas-1", system_prompt="test")
    state = AgentState(config=c, tokens=80.0, realm="research")
    memory.save_agent(state)

    loaded = memory.load_agent("a1")
    assert loaded is not None
    assert loaded.config.role == "researcher"
    assert loaded.tokens == 80.0
    assert loaded.realm == "research"


def test_load_nonexistent_agent(memory):
    assert memory.load_agent("nonexistent") is None


def test_list_alive_agents(memory):
    for i in range(3):
        c = AgentConfig(agent_id=f"a{i}", role="coder", name=f"Bolt-{i}", system_prompt="test")
        state = AgentState(config=c, alive=(i != 2))  # a2 is dead
        memory.save_agent(state)

    alive = memory.list_alive_agents()
    assert len(alive) == 2

    all_agents = memory.list_all_agents()
    assert len(all_agents) == 3


def test_list_alive_by_realm(memory):
    for i, realm in enumerate(["research", "research", "execution"]):
        c = AgentConfig(agent_id=f"a{i}", role="coder", name=f"N-{i}", system_prompt="t")
        memory.save_agent(AgentState(config=c, realm=realm))

    assert len(memory.list_alive_agents(realm="research")) == 2
    assert len(memory.list_alive_agents(realm="execution")) == 1
    assert len(memory.list_alive_agents(realm="nexus")) == 0


def test_save_and_load_task(memory):
    t = Task(task_id="t1", description="test task", goal="goal", realm="research")
    memory.save_task(t)

    tasks = memory.get_all_tasks()
    assert len(tasks) == 1
    assert tasks[0].description == "test task"


def test_get_agent_tasks(memory):
    t1 = Task(task_id="t1", description="a", goal="g", assigned_agent="a1")
    t2 = Task(task_id="t2", description="b", goal="g", assigned_agent="a2")
    memory.save_task(t1)
    memory.save_task(t2)

    assert len(memory.get_agent_tasks("a1")) == 1
    assert len(memory.get_agent_tasks("a2")) == 1


def test_transactions(memory):
    memory.record_transaction("treasury", "a1", 50.0, "reward")
    memory.record_transaction("a1", "treasury", 5.0, "tax")

    all_tx = memory.get_transactions()
    assert len(all_tx) == 2

    agent_tx = memory.get_transactions("a1")
    assert len(agent_tx) == 2


def test_economy(memory):
    memory.set_economy("money_supply", 10000.0)
    assert memory.get_economy("money_supply") == 10000.0
    assert memory.get_economy("nonexistent", 42.0) == 42.0

    memory.set_economy("money_supply", 9500.0)
    assert memory.get_economy("money_supply") == 9500.0


def test_bloodline(memory):
    memory.save_bloodline("child1", ["p1", "p2"], {"speed": 0.8}, generation=2)
    lineage = memory.get_lineage("child1")
    assert len(lineage) == 1
    assert lineage[0]["parent_ids"] == ["p1", "p2"]
    assert lineage[0]["merged_traits"]["speed"] == 0.8
