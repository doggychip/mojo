"""Async parallel task execution via ThreadPoolExecutor.

LLM calls are I/O-bound, so threads give good parallelism without
needing to convert the entire codebase to async/await.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from .models import Task

DEFAULT_MAX_WORKERS = 5


@dataclass
class TaskResult:
    """Result from a parallel task execution."""

    task: Task
    output: Optional[str] = None
    success: bool = False
    duration_s: float = 0.0
    error: Optional[str] = None


class ParallelExecutor:
    """Runs multiple tasks concurrently using a thread pool."""

    def __init__(self, max_workers: int = DEFAULT_MAX_WORKERS) -> None:
        self.max_workers = max_workers

    def execute_batch(
        self,
        tasks: List[Task],
        process_fn: Callable[[Task, int], Optional[str]],
    ) -> List[TaskResult]:
        """Execute a batch of tasks in parallel.

        Args:
            tasks: List of tasks to execute.
            process_fn: Function(task, round_num) -> output string or None on failure.

        Returns:
            List of TaskResult in original task order.
        """
        results: Dict[str, TaskResult] = {}

        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(tasks))) as pool:
            future_to_task = {}
            for i, task in enumerate(tasks):
                future = pool.submit(self._timed_execute, process_fn, task, i + 1)
                future_to_task[future] = task

            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results[task.task_id] = result
                except Exception as e:
                    results[task.task_id] = TaskResult(
                        task=task, success=False, error=str(e)
                    )

        # Return in original order
        return [results[t.task_id] for t in tasks if t.task_id in results]

    def _timed_execute(
        self,
        process_fn: Callable[[Task, int], Optional[str]],
        task: Task,
        round_num: int,
    ) -> TaskResult:
        """Execute a single task with timing."""
        start = time.monotonic()
        try:
            output = process_fn(task, round_num)
            duration = time.monotonic() - start
            return TaskResult(
                task=task,
                output=output,
                success=output is not None,
                duration_s=duration,
            )
        except Exception as e:
            duration = time.monotonic() - start
            return TaskResult(
                task=task, success=False, duration_s=duration, error=str(e)
            )


def group_by_dependency(tasks: List[Task]) -> List[List[Task]]:
    """Group tasks into independent batches that can run in parallel.

    Tasks in the same realm are considered independent of each other.
    Tasks that depend on other realms' outputs run in later batches.

    Simple heuristic: group by realm, run all same-realm tasks in parallel,
    then move to next realm priority.
    """
    realm_order = ["research", "execution", "nexus"]
    batches: List[List[Task]] = []

    for realm in realm_order:
        batch = [t for t in tasks if t.realm == realm]
        if batch:
            batches.append(batch)

    # Any tasks with unrecognized realms go in the last batch
    known = {t.task_id for batch in batches for t in batch}
    remainder = [t for t in tasks if t.task_id not in known]
    if remainder:
        batches.append(remainder)

    return batches
