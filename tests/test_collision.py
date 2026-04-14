"""Tests for collision engine."""

import json

from tests.conftest import MockLLM
from zhihuiti.collision import CollisionEngine
from zhihuiti.models import AgentConfig, AgentState


def _agent(aid):
    c = AgentConfig(agent_id=aid, role="researcher", name=f"A-{aid}", system_prompt="t")
    return AgentState(config=c)


def test_dialectic(memory):
    response = json.dumps({
        "tension": "A focuses on speed, B focuses on safety",
        "synthesis": "Staged rollout: fast for low-risk, careful for high-risk",
        "novelty": 0.7,
    })
    llm = MockLLM(responses=[response])
    engine = CollisionEngine(llm, memory)

    result = engine.collide(
        [_agent("a1"), _agent("a2")],
        ["Move fast and break things", "Move carefully and verify everything"],
        method="dialectic",
    )
    assert result["method"] == "dialectic"
    assert result["novelty"] == 0.7
    assert "synthesis" in result
    assert result["tension"] != ""


def test_adversarial(memory):
    response = json.dumps({
        "red_score": 0.7,
        "blue_score": 0.8,
        "best_of_red": "Strong cost analysis",
        "best_of_blue": "Better risk framing",
        "verdict": "Blue wins on risk but red's cost model is essential",
        "novelty": 0.6,
    })
    llm = MockLLM(responses=[response])
    engine = CollisionEngine(llm, memory)

    result = engine.collide(
        [_agent("a1"), _agent("a2")],
        ["Argument for X", "Argument against X"],
        method="adversarial",
    )
    assert result["method"] == "adversarial"
    assert result["red_score"] == 0.7
    assert result["blue_score"] == 0.8


def test_prismatic(memory):
    response = json.dumps({
        "emergent_pattern": "All lenses converge on timing as the key risk",
        "why_it_matters": "No single analysis surfaced timing as primary",
        "synthesis": "Prioritize timing over feature completeness",
        "novelty": 0.85,
    })
    llm = MockLLM(responses=[response])
    engine = CollisionEngine(llm, memory)

    result = engine.collide(
        [_agent("a1"), _agent("a2"), _agent("a3")],
        ["Economic view", "Structural view", "Temporal view"],
        method="prismatic",
    )
    assert result["method"] == "prismatic"
    assert result["novelty"] == 0.85
    assert "emergent_pattern" in result


def test_auto_collide_two_divergent(memory):
    response = json.dumps({
        "red_score": 0.6, "blue_score": 0.7,
        "best_of_red": "x", "best_of_blue": "y",
        "verdict": "combined", "novelty": 0.5,
    })
    llm = MockLLM(responses=[response])
    engine = CollisionEngine(llm, memory)

    # Two very different outputs
    result = engine.auto_collide(
        [_agent("a1"), _agent("a2")],
        ["Bitcoin is the future of finance and will replace all fiat currencies",
         "Quantum computing advances in semiconductor design for edge processors"],
    )
    assert result["method"] == "adversarial"  # high divergence


def test_auto_collide_three(memory):
    response = json.dumps({
        "emergent_pattern": "p", "why_it_matters": "m",
        "synthesis": "s", "novelty": 0.5,
    })
    llm = MockLLM(responses=[response])
    engine = CollisionEngine(llm, memory)

    result = engine.auto_collide(
        [_agent("a1"), _agent("a2"), _agent("a3")],
        ["view 1", "view 2", "view 3"],
    )
    assert result["method"] == "prismatic"


def test_collision_persisted(memory):
    response = json.dumps({
        "tension": "t", "synthesis": "s", "novelty": 0.5,
    })
    llm = MockLLM(responses=[response])
    engine = CollisionEngine(llm, memory)

    engine.collide([_agent("a1"), _agent("a2")], ["x", "y"], method="dialectic")

    collisions = memory.get_collisions()
    assert len(collisions) == 1
    assert collisions[0]["method"] == "dialectic"


def test_divergence_measure(memory):
    llm = MockLLM()
    engine = CollisionEngine(llm, memory)

    # Identical
    assert engine._measure_divergence("hello world", "hello world") == 0.0
    # Totally different
    d = engine._measure_divergence("cat dog fish", "red blue green")
    assert d == 1.0
    # Partial overlap
    d = engine._measure_divergence("the cat sat", "the dog sat")
    assert 0.0 < d < 1.0
