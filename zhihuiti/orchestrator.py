"""Main orchestration loop — wires everything together."""

import uuid
from typing import Dict, List, Optional

from .agents import AgentManager
from .behavioral import BehavioralDetector
from .bidding import Auction
from .bloodline import Bloodline
from .circuit_breaker import CircuitBreaker
from .collision import CollisionEngine
from .economy import CentralBank, RewardEngine, TaxBureau, Treasury
from .inspection import Inspector
from .judge import Judge
from .lending import FuturesMarket, LoanManager
from .llm import LLM
from .memory import Memory
from .models import AgentState, Task
from .prompts import GOVERNOR_DECOMPOSE_PROMPT
from .parallel import ParallelExecutor, group_by_dependency
from .realms import RealmRouter
from .relationships import RelationshipManager


class Orchestrator:
    """Core loop: goal → decompose → bid → execute → inspect → reward."""

    def __init__(
        self,
        llm: Optional[LLM] = None,
        memory: Optional[Memory] = None,
        db_path: str = "zhihuiti.db",
    ) -> None:
        self.llm = llm or LLM()
        self.memory = memory or Memory(db_path)

        # Economy
        self.bank = CentralBank(self.memory)
        self.treasury = Treasury(self.memory)
        self.tax_bureau = TaxBureau(self.memory, self.treasury)
        self.reward_engine = RewardEngine(self.treasury, self.tax_bureau, self.memory)
        self.bank.initialize()

        # Agents & systems
        self.agents = AgentManager(self.llm, self.memory)
        self.judge = Judge(self.llm)
        self.auction = Auction()
        self.realm_router = RealmRouter(self.memory)
        self.bloodline = Bloodline(self.memory)
        self.inspector = Inspector(self.llm, stop_on_fail=True)
        self.circuit_breaker = CircuitBreaker()
        self.behavioral = BehavioralDetector()

        # M5: Advanced economics
        self.loan_manager = LoanManager(self.memory)
        self.futures_market = FuturesMarket(self.memory)
        self.relationships = RelationshipManager(self.memory)
        self.collision_engine = CollisionEngine(self.llm, self.memory)

    def run(self, goal: str, max_rounds: int = 10) -> str:
        """Execute a goal through the full orchestration pipeline."""
        print(f"\n{'='*60}")
        print(f"  智慧体 ORCHESTRATOR")
        print(f"  Goal: {goal}")
        print(f"{'='*60}\n")

        # 1. Decompose goal into tasks
        tasks = self._decompose_goal(goal)
        if not tasks:
            return "[Error] Failed to decompose goal into tasks."

        print(f"📋 Decomposed into {len(tasks)} tasks:\n")
        for i, t in enumerate(tasks, 1):
            print(f"   {i}. [{t.realm}] {t.description}")
        print()

        # 2. Process each task through the pipeline
        results: List[str] = []
        for round_num, task in enumerate(tasks, 1):
            if round_num > max_rounds:
                print(f"⚠️  Max rounds ({max_rounds}) reached. Stopping.")
                break

            result = self._process_task(task, round_num)
            if result:
                results.append(result)

        # 3. Synthesize final output
        if not results:
            return "[Error] No tasks completed successfully."

        print(f"\n{'='*60}")
        print("  SYNTHESIZING RESULTS")
        print(f"{'='*60}\n")

        final = self.agents.synthesize(results)

        # 4. Lifecycle checks (cull/promote)
        self._lifecycle_check()

        print(f"\n{'='*60}")
        print("  FINAL OUTPUT")
        print(f"{'='*60}\n")
        print(final)

        return final

    def run_parallel(self, goal: str, max_rounds: int = 10, max_workers: int = 5) -> str:
        """Execute a goal with parallel task processing within each realm batch."""
        print(f"\n{'='*60}")
        print(f"  智慧体 ORCHESTRATOR (PARALLEL)")
        print(f"  Goal: {goal}")
        print(f"  Workers: {max_workers}")
        print(f"{'='*60}\n")

        # 1. Decompose goal into tasks
        tasks = self._decompose_goal(goal)
        if not tasks:
            return "[Error] Failed to decompose goal into tasks."

        print(f"📋 Decomposed into {len(tasks)} tasks:\n")
        for i, t in enumerate(tasks, 1):
            print(f"   {i}. [{t.realm}] {t.description}")

        # 2. Group into parallel batches by realm dependency
        batches = group_by_dependency(tasks)
        print(f"\n⚡ Grouped into {len(batches)} parallel batches")

        executor = ParallelExecutor(max_workers=max_workers)
        all_results: List[str] = []
        task_count = 0

        for batch_num, batch in enumerate(batches, 1):
            if task_count >= max_rounds:
                print(f"\n⚠️  Max rounds ({max_rounds}) reached. Stopping.")
                break

            remaining = max_rounds - task_count
            batch = batch[:remaining]

            print(f"\n{'─'*40}")
            print(f"  Batch {batch_num}: {len(batch)} tasks ({batch[0].realm})")
            print(f"{'─'*40}")

            # Run all tasks in this batch concurrently
            batch_results = executor.execute_batch(batch, self._process_task)

            for tr in batch_results:
                task_count += 1
                status_icon = "✅" if tr.success else "❌"
                print(f"   {status_icon} {tr.task.description[:50]}... ({tr.duration_s:.1f}s)")
                if tr.output:
                    all_results.append(tr.output)

        # 3. Synthesize
        if not all_results:
            return "[Error] No tasks completed successfully."

        print(f"\n{'='*60}")
        print("  SYNTHESIZING RESULTS")
        print(f"{'='*60}\n")

        final = self.agents.synthesize(all_results)

        # 4. Lifecycle checks
        self._lifecycle_check()

        print(f"\n{'='*60}")
        print("  FINAL OUTPUT")
        print(f"{'='*60}\n")
        print(final)

        return final

    def _decompose_goal(self, goal: str) -> List[Task]:
        """Use governor LLM to decompose a goal into tasks."""
        print("🧠 Decomposing goal into tasks...")
        raw = self.llm.call_json(
            GOVERNOR_DECOMPOSE_PROMPT,
            f"GOAL: {goal}",
            temperature=0.5,
        )

        # Handle both list and error dict responses
        if isinstance(raw, dict) and "error" in raw:
            print(f"   ⚠️  Parse error, attempting raw extraction...")
            # Try to extract from raw text
            raw_text = raw.get("raw", "")
            return self._fallback_decompose(goal, raw_text)

        if not isinstance(raw, list):
            return self._fallback_decompose(goal, str(raw))

        tasks = []
        for item in raw:
            task = Task(
                task_id=str(uuid.uuid4())[:8],
                description=item.get("description", ""),
                goal=goal,
                realm=item.get("realm", "execution"),
            )
            self.memory.save_task(task)
            tasks.append(task)

        return tasks

    def _fallback_decompose(self, goal: str, raw_text: str) -> List[Task]:
        """Fallback: create a single task from the goal."""
        task = Task(
            task_id=str(uuid.uuid4())[:8],
            description=goal,
            goal=goal,
            realm="execution",
        )
        self.memory.save_task(task)
        return [task]

    def _process_task(self, task: Task, round_num: int) -> Optional[str]:
        """Process a single task through bid → execute → inspect → reward."""
        realm = self.realm_router.route_task(task)
        task.realm = realm

        print(f"\n--- Round {round_num}: [{realm}] {task.description[:60]}... ---")

        # Ensure agents exist in this realm
        agents = self.agents.ensure_agents_for_realm(realm)

        # Run auction
        winner = self.auction.run(agents, task)
        if not winner:
            print(f"   ❌ No bids received. Spawning fresh agent.")
            winner = self.agents.spawn(role="researcher", realm=realm)

        task.assigned_agent = winner.config.agent_id
        task.status = "running"
        self.memory.save_task(task)
        print(f"   🏆 Winner: {winner.config.name} ({winner.config.role})")

        # Execute
        output = self.agents.execute(winner, task)

        # Circuit breaker (FREE)
        safe, triggered = self.circuit_breaker.scan(output)
        if not safe:
            print(f"   🚨 Circuit breaker: {triggered}")
            task.status = "failed"
            self.memory.save_task(task)
            winner.tasks_failed += 1
            self.memory.save_agent(winner)
            return None

        # Behavioral check (FREE)
        behavior = self.behavioral.check(task, output)
        if behavior["flags"]:
            print(f"   ⚠️  Behavioral flags: {behavior['flags']}")
            # Penalize but don't reject unless severe
            winner.total_score -= behavior["penalty"]

        # 3-layer inspection (LLM calls)
        passed, inspection_results = self.inspector.inspect(task, output)
        for layer in inspection_results:
            status = "✅" if layer["passed"] else "❌"
            print(f"   {status} {layer['layer']}: {layer['score']:.2f}")

        if not passed:
            print(f"   ❌ Inspection failed. Rejecting output.")
            task.status = "failed"
            self.memory.save_task(task)
            winner.tasks_failed += 1
            self.memory.save_agent(winner)
            return None

        # Judge scoring
        judgment = self.judge.score(task, output)
        score = judgment["score"]
        print(f"   📊 Judge score: {score:.2f} — {judgment['feedback'][:80]}")

        # Pay reward
        net_reward = self.reward_engine.pay_reward(winner, score)
        print(f"   💰 Net reward: {net_reward:.1f} tokens")

        # Update task and agent
        task.status = "completed"
        task.result = output
        task.score = score
        self.memory.save_task(task)

        winner.tasks_completed += 1
        winner.total_score += score
        self.memory.save_agent(winner)

        # Settle any futures bets on this task
        settled = self.futures_market.settle(task.task_id, score)
        for s in settled:
            status_icon = "📈" if s["status"] == "won" else "📉"
            print(f"   {status_icon} Future {s['future_id']}: {s['status']} (payout: {s['payout']:.1f})")

        # Check loan defaults
        defaults = self.loan_manager.check_defaults(winner)
        for d in defaults:
            print(f"   🏦 Loan {d['loan_id']} defaulted!")

        return output

    def _lifecycle_check(self) -> None:
        """Run cull and promote checks on all agents."""
        for agent in self.memory.list_alive_agents():
            if self.agents.check_cull(agent):
                print(f"   💀 Culled: {agent.config.name}")
            new_realm = self.agents.check_promote(agent)
            if new_realm:
                print(f"   ⬆️  Promoted: {agent.config.name} → {new_realm}")

    def status(self) -> Dict:
        """Get system status summary."""
        agents = self.memory.list_all_agents()
        alive = [a for a in agents if a.alive]
        tasks = self.memory.get_all_tasks()
        economy = self.memory.get_all_economy()

        return {
            "agents": {
                "total": len(agents),
                "alive": len(alive),
                "by_realm": {
                    realm: len([a for a in alive if a.realm == realm])
                    for realm in ["research", "execution", "nexus"]
                },
            },
            "tasks": {
                "total": len(tasks),
                "completed": len([t for t in tasks if t.status == "completed"]),
                "failed": len([t for t in tasks if t.status == "failed"]),
                "pending": len([t for t in tasks if t.status == "pending"]),
            },
            "economy": economy,
            "loans": {
                "active": len(self.memory.get_loans(status="active")),
                "repaid": len(self.memory.get_loans(status="repaid")),
                "defaulted": len(self.memory.get_loans(status="defaulted")),
            },
            "futures": {
                "open": len(self.memory.get_futures(status="open")),
                "won": len(self.memory.get_futures(status="won")),
                "lost": len(self.memory.get_futures(status="lost")),
            },
            "relationships": self.relationships.get_network_summary(),
            "collisions": len(self.memory.get_collisions(limit=100)),
        }
