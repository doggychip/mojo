"""FastAPI backend for zhihuiti dashboard."""

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .memory import Memory
from .realms import REALM_CONFIG, RealmRouter

DASHBOARD_DIR = Path(__file__).parent / "dashboard"


def create_app(db_path: str = "zhihuiti.db") -> FastAPI:
    """Create and configure the FastAPI app."""
    app = FastAPI(title="智慧体 Dashboard", version="0.2.0")
    memory = Memory(db_path)
    realm_router = RealmRouter(memory)

    # --- Dashboard HTML ---

    @app.get("/", response_class=HTMLResponse)
    def dashboard() -> HTMLResponse:
        index = DASHBOARD_DIR / "index.html"
        return HTMLResponse(content=index.read_text(encoding="utf-8"))

    # --- API endpoints ---

    @app.get("/api/status")
    def get_status() -> dict:
        agents = memory.list_all_agents()
        alive = [a for a in agents if a.alive]
        tasks = memory.get_all_tasks()
        economy = memory.get_all_economy()
        return {
            "agents": {
                "total": len(agents),
                "alive": len(alive),
                "by_realm": {
                    r: len([a for a in alive if a.realm == r])
                    for r in ["research", "execution", "nexus"]
                },
            },
            "tasks": {
                "total": len(tasks),
                "completed": len([t for t in tasks if t.status == "completed"]),
                "failed": len([t for t in tasks if t.status == "failed"]),
                "pending": len([t for t in tasks if t.status == "pending"]),
                "running": len([t for t in tasks if t.status == "running"]),
            },
            "economy": economy,
        }

    @app.get("/api/agents")
    def get_agents(realm: Optional[str] = Query(None), alive_only: bool = Query(True)) -> list:
        if alive_only:
            agents = memory.list_alive_agents(realm=realm)
        else:
            agents = memory.list_all_agents()
            if realm:
                agents = [a for a in agents if a.realm == realm]
        return [
            {
                "agent_id": a.config.agent_id,
                "name": a.config.name,
                "role": a.config.role,
                "realm": a.realm,
                "tokens": round(a.tokens, 1),
                "average_score": round(a.average_score, 2),
                "tasks_completed": a.tasks_completed,
                "tasks_failed": a.tasks_failed,
                "alive": a.alive,
                "generation": a.generation,
            }
            for a in agents
        ]

    @app.get("/api/tasks")
    def get_tasks(status: Optional[str] = Query(None), limit: int = Query(50)) -> list:
        tasks = memory.get_all_tasks()
        if status:
            tasks = [t for t in tasks if t.status == status]
        tasks = tasks[-limit:]  # most recent
        return [
            {
                "task_id": t.task_id,
                "description": t.description,
                "goal": t.goal,
                "status": t.status,
                "score": round(t.score, 2),
                "realm": t.realm,
                "assigned_agent": t.assigned_agent,
            }
            for t in tasks
        ]

    @app.get("/api/economy")
    def get_economy() -> dict:
        metrics = memory.get_all_economy()
        transactions = memory.get_transactions()
        return {
            "metrics": metrics,
            "recent_transactions": transactions[-20:],
        }

    @app.get("/api/realms")
    def get_realms() -> dict:
        return realm_router.get_realm_stats()

    @app.get("/api/agent/{agent_id}")
    def get_agent_detail(agent_id: str) -> dict:
        agent = memory.load_agent(agent_id)
        if agent is None:
            return {"error": "Agent not found"}
        tasks = memory.get_agent_tasks(agent_id)
        txns = memory.get_transactions(agent_id)
        return {
            "agent": {
                "agent_id": agent.config.agent_id,
                "name": agent.config.name,
                "role": agent.config.role,
                "realm": agent.realm,
                "tokens": round(agent.tokens, 1),
                "average_score": round(agent.average_score, 2),
                "tasks_completed": agent.tasks_completed,
                "tasks_failed": agent.tasks_failed,
                "alive": agent.alive,
                "generation": agent.generation,
                "gene_traits": agent.config.gene_traits,
                "parent_ids": agent.parent_ids,
            },
            "tasks": [
                {"task_id": t.task_id, "description": t.description, "status": t.status, "score": round(t.score, 2)}
                for t in tasks
            ],
            "transactions": txns[-10:],
        }

    @app.get("/api/bloodline/{agent_id}")
    def get_bloodline(agent_id: str) -> list:
        return memory.get_lineage(agent_id)

    return app
