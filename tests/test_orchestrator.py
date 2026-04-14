"""Tests for orchestrator with mocked LLM."""

import json

from tests.conftest import MockLLM
from zhihuiti.orchestrator import Orchestrator


def test_orchestrator_initializes(memory):
    llm = MockLLM()
    orch = Orchestrator(llm=llm, memory=memory)
    assert orch.treasury.balance == 10_000.0
    s = orch.status()
    assert s["agents"]["alive"] == 0


def test_decompose_goal(memory):
    tasks_json = json.dumps([
        {"description": "Research Bitcoin history", "role": "researcher", "realm": "research"},
        {"description": "Summarize key features", "role": "writer", "realm": "execution"},
    ])
    llm = MockLLM(responses=[tasks_json])
    orch = Orchestrator(llm=llm, memory=memory)

    tasks = orch._decompose_goal("Summarize Bitcoin")
    assert len(tasks) == 2
    assert tasks[0].realm == "research"
    assert tasks[1].realm == "execution"


def test_decompose_fallback(memory):
    llm = MockLLM(responses=["This is not valid JSON at all"])
    orch = Orchestrator(llm=llm, memory=memory)

    tasks = orch._decompose_goal("Do something")
    assert len(tasks) == 1  # fallback single task


def test_full_run(memory):
    """End-to-end run with mock LLM."""
    responses = [
        # 1. Decompose goal
        json.dumps([
            {"description": "Research topic", "role": "researcher", "realm": "research"},
        ]),
        # 2. Agent executes task
        "Here is my detailed research on the topic with multiple findings and evidence.",
        # 3. Inspection layer 1 (accuracy)
        json.dumps({"score": 0.8, "issues": "none"}),
        # 4. Inspection layer 2 (quality)
        json.dumps({"score": 0.75, "issues": "none"}),
        # 5. Inspection layer 3 (integrity)
        json.dumps({"score": 0.9, "issues": "none"}),
        # 6. Judge scoring
        json.dumps({"score": 0.8, "feedback": "Good work"}),
    ]
    llm = MockLLM(responses=responses)
    orch = Orchestrator(llm=llm, memory=memory)

    result = orch.run("Test goal", max_rounds=5)
    assert isinstance(result, str)
    assert len(result) > 0

    # Check state after run
    s = orch.status()
    assert s["tasks"]["completed"] >= 1
    assert s["agents"]["alive"] >= 1
