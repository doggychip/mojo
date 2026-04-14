"""Tests for FastAPI dashboard API."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from zhihuiti.api import create_app
from zhihuiti.economy import CentralBank
from zhihuiti.memory import Memory
from zhihuiti.models import AgentConfig, AgentState, Task


@pytest.fixture
def client():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    app = create_app(db_path=tmp.name)
    # Seed some data
    mem = Memory(tmp.name)
    bank = CentralBank(mem)
    bank.initialize()

    # Add agents
    for i, (role, realm) in enumerate([
        ("researcher", "research"),
        ("coder", "execution"),
        ("analyst", "research"),
        ("governor", "nexus"),
    ]):
        c = AgentConfig(agent_id=f"a{i}", role=role, name=f"Agent-{i}", system_prompt="test")
        state = AgentState(config=c, tokens=80.0 + i * 10, realm=realm,
                           tasks_completed=i + 1, total_score=0.7 * (i + 1))
        mem.save_agent(state)

    # Add tasks
    for i, status in enumerate(["completed", "completed", "failed", "pending"]):
        t = Task(task_id=f"t{i}", description=f"Task {i}", goal="test",
                 status=status, score=0.8 if status == "completed" else 0.0,
                 realm="execution", assigned_agent=f"a{i % 4}")
        mem.save_task(t)

    # Add a transaction
    mem.record_transaction("treasury", "a0", 40.0, "task_reward")

    yield TestClient(app)
    mem.close()
    os.unlink(tmp.name)


def test_dashboard_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "智慧体" in resp.text


def test_status(client):
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["agents"]["alive"] == 4
    assert data["agents"]["by_realm"]["research"] == 2
    assert data["tasks"]["completed"] == 2
    assert data["tasks"]["failed"] == 1
    assert data["economy"]["money_supply"] == 10000.0


def test_agents_list(client):
    resp = client.get("/api/agents")
    assert resp.status_code == 200
    agents = resp.json()
    assert len(agents) == 4
    assert all("name" in a for a in agents)
    assert all("tokens" in a for a in agents)


def test_agents_filter_realm(client):
    resp = client.get("/api/agents?realm=research")
    agents = resp.json()
    assert len(agents) == 2
    assert all(a["realm"] == "research" for a in agents)


def test_agents_include_dead(client):
    resp = client.get("/api/agents?alive_only=false")
    agents = resp.json()
    assert len(agents) == 4  # all alive in this fixture


def test_tasks(client):
    resp = client.get("/api/tasks")
    tasks = resp.json()
    assert len(tasks) == 4
    assert all("task_id" in t for t in tasks)


def test_tasks_filter_status(client):
    resp = client.get("/api/tasks?status=completed")
    tasks = resp.json()
    assert len(tasks) == 2
    assert all(t["status"] == "completed" for t in tasks)


def test_economy(client):
    resp = client.get("/api/economy")
    data = resp.json()
    assert data["metrics"]["treasury_balance"] == 10000.0
    assert len(data["recent_transactions"]) == 1
    assert data["recent_transactions"][0]["amount"] == 40.0


def test_realms(client):
    resp = client.get("/api/realms")
    data = resp.json()
    assert "research" in data
    assert "execution" in data
    assert "nexus" in data
    assert data["research"]["agent_count"] == 2


def test_agent_detail(client):
    resp = client.get("/api/agent/a0")
    data = resp.json()
    assert data["agent"]["name"] == "Agent-0"
    assert data["agent"]["role"] == "researcher"
    assert len(data["tasks"]) >= 1
    assert len(data["transactions"]) >= 1


def test_agent_not_found(client):
    resp = client.get("/api/agent/nonexistent")
    data = resp.json()
    assert "error" in data


def test_bloodline_empty(client):
    resp = client.get("/api/bloodline/a0")
    data = resp.json()
    assert data == []
