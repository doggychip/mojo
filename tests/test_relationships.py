"""Tests for agent relationships."""

import pytest

from zhihuiti.models import AgentConfig, AgentState
from zhihuiti.relationships import RelationshipManager


def _agent(aid):
    c = AgentConfig(agent_id=aid, role="coder", name=f"A-{aid}", system_prompt="t")
    return AgentState(config=c)


def test_form_relationship(memory):
    rm = RelationshipManager(memory)
    rm.form("a1", "a2", "ally", strength=0.7)

    rels = rm.get("a1")
    assert len(rels) == 1
    assert rels[0]["rel_type"] == "ally"
    assert rels[0]["strength"] == 0.7


def test_invalid_type(memory):
    rm = RelationshipManager(memory)
    with pytest.raises(ValueError):
        rm.form("a1", "a2", "bestfriend")


def test_bidirectional_lookup(memory):
    rm = RelationshipManager(memory)
    rm.form("a1", "a2", "mentor")

    assert len(rm.get("a1")) == 1
    assert len(rm.get("a2")) == 1  # can find from either side


def test_strengthen_and_weaken(memory):
    rm = RelationshipManager(memory)
    rm.form("a1", "a2", "partner", strength=0.5)

    rm.strengthen("a1", "a2", "partner")
    rels = rm.get("a1", "partner")
    assert rels[0]["strength"] == 0.55

    rm.weaken("a1", "a2", "partner")
    rels = rm.get("a1", "partner")
    assert abs(rels[0]["strength"] - 0.50) < 0.01


def test_get_bid_modifier(memory):
    rm = RelationshipManager(memory)
    a1 = _agent("a1")
    a2 = _agent("a2")
    rm.form("a1", "a2", "rival", strength=0.8)

    modifier = rm.get_bid_modifier(a1, a2)
    assert modifier < 0  # rivals bid cheaper


def test_synthesis_weight(memory):
    rm = RelationshipManager(memory)
    a1 = _agent("a1")
    a2 = _agent("a2")
    rm.form("a1", "a2", "ally", strength=0.9)

    weight = rm.get_synthesis_weight(a1, [a2])
    assert weight > 0  # allies boost synthesis


def test_on_task_success_creates_partner(memory):
    rm = RelationshipManager(memory)
    rm.on_task_success("a1", "a2")

    rels = rm.get("a1", "partner")
    assert len(rels) == 1
    assert rels[0]["strength"] == 0.3


def test_on_task_success_strengthens_existing(memory):
    rm = RelationshipManager(memory)
    rm.form("a1", "a2", "partner", strength=0.5)
    rm.on_task_success("a1", "a2")

    rels = rm.get("a1", "partner")
    assert rels[0]["strength"] == 0.55


def test_on_task_conflict_creates_rival(memory):
    rm = RelationshipManager(memory)
    rm.on_task_conflict("a1", "a2")

    rels = rm.get("a1", "rival")
    assert len(rels) == 1


def test_nemesis_escalation(memory):
    rm = RelationshipManager(memory)
    rm.form("a1", "a2", "rival", strength=0.85)
    rm.on_task_conflict("a1", "a2")

    nemesis_rels = rm.get("a1", "nemesis")
    assert len(nemesis_rels) == 1


def test_on_inspection(memory):
    rm = RelationshipManager(memory)
    rm.on_inspection("judge1", "worker1", passed=True)

    rels = rm.get("judge1", "inspector")
    assert len(rels) == 1


def test_network_summary(memory):
    rm = RelationshipManager(memory)
    rm.form("a1", "a2", "ally")
    rm.form("a1", "a3", "rival")
    rm.form("a2", "a3", "mentor")

    summary = rm.get_network_summary()
    assert summary["total"] == 3
    assert summary["by_type"]["ally"] == 1
    assert summary["by_type"]["rival"] == 1
    assert summary["avg_strength"] == 0.5
