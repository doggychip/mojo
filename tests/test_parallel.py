"""Tests for parallel task execution."""

import json
import time
from typing import Optional

from tests.conftest import MockLLM
from zhihuiti.models import Task
from zhihuiti.orchestrator import Orchestrator
from zhihuiti.parallel import ParallelExecutor, TaskResult, group_by_dependency


def test_group_by_dependency():
    tasks = [
        Task(task_id="t1", description="a", goal="g", realm="research"),
        Task(task_id="t2", description="b", goal="g", realm="execution"),
        Task(task_id="t3", description="c", goal="g", realm="research"),
        Task(task_id="t4", description="d", goal="g", realm="nexus"),
    ]
    batches = group_by_dependency(tasks)
    assert len(batches) == 3
    assert len(batches[0]) == 2  # research
    assert len(batches[1]) == 1  # execution
    assert len(batches[2]) == 1  # nexus
    assert all(t.realm == "research" for t in batches[0])


def test_group_single_realm():
    tasks = [
        Task(task_id="t1", description="a", goal="g", realm="execution"),
        Task(task_id="t2", description="b", goal="g", realm="execution"),
    ]
    batches = group_by_dependency(tasks)
    assert len(batches) == 1
    assert len(batches[0]) == 2


def test_parallel_executor_basic():
    executor = ParallelExecutor(max_workers=3)
    tasks = [
        Task(task_id=f"t{i}", description=f"task {i}", goal="g")
        for i in range(4)
    ]

    def process(task: Task, round_num: int) -> Optional[str]:
        return f"result for {task.task_id}"

    results = executor.execute_batch(tasks, process)
    assert len(results) == 4
    assert all(r.success for r in results)
    assert all(r.output is not None for r in results)


def test_parallel_executor_preserves_order():
    executor = ParallelExecutor(max_workers=3)
    tasks = [
        Task(task_id=f"t{i}", description=f"task {i}", goal="g")
        for i in range(5)
    ]

    def process(task: Task, round_num: int) -> Optional[str]:
        return task.task_id

    results = executor.execute_batch(tasks, process)
    assert [r.output for r in results] == ["t0", "t1", "t2", "t3", "t4"]


def test_parallel_executor_handles_failure():
    executor = ParallelExecutor(max_workers=2)
    tasks = [
        Task(task_id="ok", description="good", goal="g"),
        Task(task_id="fail", description="bad", goal="g"),
    ]

    def process(task: Task, round_num: int) -> Optional[str]:
        if task.task_id == "fail":
            return None
        return "success"

    results = executor.execute_batch(tasks, process)
    assert len(results) == 2
    assert results[0].success is True
    assert results[1].success is False


def test_parallel_executor_handles_exception():
    executor = ParallelExecutor(max_workers=2)
    tasks = [
        Task(task_id="ok", description="good", goal="g"),
        Task(task_id="boom", description="explode", goal="g"),
    ]

    def process(task: Task, round_num: int) -> Optional[str]:
        if task.task_id == "boom":
            raise ValueError("kaboom")
        return "success"

    results = executor.execute_batch(tasks, process)
    assert len(results) == 2
    ok_result = next(r for r in results if r.task.task_id == "ok")
    boom_result = next(r for r in results if r.task.task_id == "boom")
    assert ok_result.success is True
    assert boom_result.success is False
    assert "kaboom" in boom_result.error


def test_parallel_actually_concurrent():
    """Verify tasks run concurrently, not sequentially."""
    executor = ParallelExecutor(max_workers=3)
    tasks = [
        Task(task_id=f"t{i}", description=f"task {i}", goal="g")
        for i in range(3)
    ]

    def slow_process(task: Task, round_num: int) -> Optional[str]:
        time.sleep(0.1)
        return "done"

    start = time.monotonic()
    results = executor.execute_batch(tasks, slow_process)
    elapsed = time.monotonic() - start

    assert all(r.success for r in results)
    # 3 tasks at 0.1s each: sequential = 0.3s, parallel < 0.25s
    assert elapsed < 0.25, f"Took {elapsed:.2f}s — not running in parallel"


def test_parallel_run_end_to_end(memory):
    """Full orchestrator.run_parallel with mocked LLM."""
    responses = [
        # Decompose
        json.dumps([
            {"description": "Research A", "role": "researcher", "realm": "research"},
            {"description": "Research B", "role": "analyst", "realm": "research"},
            {"description": "Execute C", "role": "coder", "realm": "execution"},
        ]),
        # Task 1 execute
        "Research A output with detailed findings and analysis.",
        # Task 1 inspection x3
        json.dumps({"score": 0.8, "issues": "none"}),
        json.dumps({"score": 0.75, "issues": "none"}),
        json.dumps({"score": 0.9, "issues": "none"}),
        # Task 1 judge
        json.dumps({"score": 0.8, "feedback": "Good"}),
        # Task 2 execute
        "Research B output with quantitative analysis.",
        # Task 2 inspection x3
        json.dumps({"score": 0.7, "issues": "none"}),
        json.dumps({"score": 0.8, "issues": "none"}),
        json.dumps({"score": 0.85, "issues": "none"}),
        # Task 2 judge
        json.dumps({"score": 0.75, "feedback": "Solid"}),
        # Task 3 execute
        "Execute C output with implementation details.",
        # Task 3 inspection x3
        json.dumps({"score": 0.9, "issues": "none"}),
        json.dumps({"score": 0.85, "issues": "none"}),
        json.dumps({"score": 0.8, "issues": "none"}),
        # Task 3 judge
        json.dumps({"score": 0.85, "feedback": "Great"}),
        # Synthesis
        "Combined output from all three tasks.",
    ]
    llm = MockLLM(responses=responses)
    orch = Orchestrator(llm=llm, memory=memory)

    result = orch.run_parallel("Test parallel goal", max_rounds=10, max_workers=3)
    assert isinstance(result, str)
    assert len(result) > 0

    s = orch.status()
    assert s["tasks"]["completed"] >= 1
