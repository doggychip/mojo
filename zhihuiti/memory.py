"""SQLite persistence layer for zhihuiti."""

import json
import sqlite3
from typing import Dict, List, Optional

from .models import AgentConfig, AgentState, Task


class Memory:
    """SQLite-backed storage for agents, tasks, transactions, bloodline, and economy."""

    def __init__(self, db_path: str = "zhihuiti.db") -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        cur = self.conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                name TEXT NOT NULL,
                system_prompt TEXT,
                budget REAL DEFAULT 100.0,
                depth INTEGER DEFAULT 0,
                gene_traits TEXT DEFAULT '{}',
                tokens REAL DEFAULT 100.0,
                total_score REAL DEFAULT 0.0,
                tasks_completed INTEGER DEFAULT 0,
                tasks_failed INTEGER DEFAULT 0,
                realm TEXT DEFAULT 'execution',
                alive INTEGER DEFAULT 1,
                generation INTEGER DEFAULT 1,
                parent_ids TEXT DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                goal TEXT NOT NULL,
                context TEXT DEFAULT '',
                assigned_agent TEXT,
                status TEXT DEFAULT 'pending',
                result TEXT,
                score REAL DEFAULT 0.0,
                realm TEXT DEFAULT 'execution'
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_id TEXT,
                to_id TEXT,
                amount REAL NOT NULL,
                reason TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS bloodline (
                child_id TEXT NOT NULL,
                parent_ids TEXT NOT NULL,
                merged_traits TEXT DEFAULT '{}',
                generation INTEGER DEFAULT 1,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS economy (
                key TEXT PRIMARY KEY,
                value REAL NOT NULL
            );
        """)
        self.conn.commit()

    # --- Agent CRUD ---

    def save_agent(self, state: AgentState) -> None:
        """Insert or replace an agent state."""
        c = state.config
        self.conn.execute(
            """INSERT OR REPLACE INTO agents
               (agent_id, role, name, system_prompt, budget, depth, gene_traits,
                tokens, total_score, tasks_completed, tasks_failed,
                realm, alive, generation, parent_ids)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                c.agent_id, c.role, c.name, c.system_prompt, c.budget, c.depth,
                json.dumps(c.gene_traits),
                state.tokens, state.total_score, state.tasks_completed,
                state.tasks_failed, state.realm, int(state.alive),
                state.generation, json.dumps(state.parent_ids),
            ),
        )
        self.conn.commit()

    def load_agent(self, agent_id: str) -> Optional[AgentState]:
        """Load an agent by ID, or None if not found."""
        row = self.conn.execute(
            "SELECT * FROM agents WHERE agent_id = ?", (agent_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_agent(row)

    def list_alive_agents(self, realm: Optional[str] = None) -> List[AgentState]:
        """List all living agents, optionally filtered by realm."""
        if realm:
            rows = self.conn.execute(
                "SELECT * FROM agents WHERE alive = 1 AND realm = ?", (realm,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM agents WHERE alive = 1"
            ).fetchall()
        return [self._row_to_agent(r) for r in rows]

    def list_all_agents(self) -> List[AgentState]:
        """List all agents including dead ones."""
        rows = self.conn.execute("SELECT * FROM agents").fetchall()
        return [self._row_to_agent(r) for r in rows]

    def _row_to_agent(self, row: sqlite3.Row) -> AgentState:
        config = AgentConfig(
            agent_id=row["agent_id"],
            role=row["role"],
            name=row["name"],
            system_prompt=row["system_prompt"],
            budget=row["budget"],
            depth=row["depth"],
            gene_traits=json.loads(row["gene_traits"]),
        )
        return AgentState(
            config=config,
            tokens=row["tokens"],
            total_score=row["total_score"],
            tasks_completed=row["tasks_completed"],
            tasks_failed=row["tasks_failed"],
            realm=row["realm"],
            alive=bool(row["alive"]),
            generation=row["generation"],
            parent_ids=json.loads(row["parent_ids"]),
        )

    # --- Task CRUD ---

    def save_task(self, task: Task) -> None:
        """Insert or replace a task."""
        self.conn.execute(
            """INSERT OR REPLACE INTO tasks
               (task_id, description, goal, context, assigned_agent, status, result, score, realm)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                task.task_id, task.description, task.goal, task.context,
                task.assigned_agent, task.status, task.result, task.score, task.realm,
            ),
        )
        self.conn.commit()

    def get_agent_tasks(self, agent_id: str) -> List[Task]:
        """Get all tasks assigned to an agent."""
        rows = self.conn.execute(
            "SELECT * FROM tasks WHERE assigned_agent = ?", (agent_id,)
        ).fetchall()
        return [self._row_to_task(r) for r in rows]

    def get_all_tasks(self) -> List[Task]:
        """Get all tasks."""
        rows = self.conn.execute("SELECT * FROM tasks").fetchall()
        return [self._row_to_task(r) for r in rows]

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        return Task(
            task_id=row["task_id"],
            description=row["description"],
            goal=row["goal"],
            context=row["context"],
            assigned_agent=row["assigned_agent"],
            status=row["status"],
            result=row["result"],
            score=row["score"],
            realm=row["realm"],
        )

    # --- Transactions ---

    def record_transaction(self, from_id: str, to_id: str, amount: float, reason: str) -> None:
        """Record a token transfer."""
        self.conn.execute(
            "INSERT INTO transactions (from_id, to_id, amount, reason) VALUES (?,?,?,?)",
            (from_id, to_id, amount, reason),
        )
        self.conn.commit()

    def get_transactions(self, agent_id: Optional[str] = None) -> List[Dict]:
        """Get transaction history, optionally filtered by agent."""
        if agent_id:
            rows = self.conn.execute(
                "SELECT * FROM transactions WHERE from_id = ? OR to_id = ?",
                (agent_id, agent_id),
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM transactions").fetchall()
        return [dict(r) for r in rows]

    # --- Bloodline ---

    def save_bloodline(self, child_id: str, parent_ids: List[str], merged_traits: Dict, generation: int = 1) -> None:
        """Record a bloodline entry."""
        self.conn.execute(
            "INSERT INTO bloodline (child_id, parent_ids, merged_traits, generation) VALUES (?,?,?,?)",
            (child_id, json.dumps(parent_ids), json.dumps(merged_traits), generation),
        )
        self.conn.commit()

    def get_lineage(self, agent_id: str, max_generations: int = 7) -> List[Dict]:
        """Trace lineage up to max_generations back."""
        lineage = []
        current_ids = [agent_id]
        for _ in range(max_generations):
            if not current_ids:
                break
            placeholders = ",".join("?" for _ in current_ids)
            rows = self.conn.execute(
                f"SELECT * FROM bloodline WHERE child_id IN ({placeholders})",
                current_ids,
            ).fetchall()
            if not rows:
                break
            next_ids = []
            for r in rows:
                entry = dict(r)
                entry["parent_ids"] = json.loads(entry["parent_ids"])
                entry["merged_traits"] = json.loads(entry["merged_traits"])
                lineage.append(entry)
                next_ids.extend(entry["parent_ids"])
            current_ids = next_ids
        return lineage

    # --- Economy ---

    def set_economy(self, key: str, value: float) -> None:
        """Set an economy metric."""
        self.conn.execute(
            "INSERT OR REPLACE INTO economy (key, value) VALUES (?,?)", (key, value)
        )
        self.conn.commit()

    def get_economy(self, key: str, default: float = 0.0) -> float:
        """Get an economy metric."""
        row = self.conn.execute(
            "SELECT value FROM economy WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def get_all_economy(self) -> Dict[str, float]:
        """Get all economy metrics."""
        rows = self.conn.execute("SELECT * FROM economy").fetchall()
        return {r["key"]: r["value"] for r in rows}

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()
