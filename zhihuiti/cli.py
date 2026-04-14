"""Click CLI for zhihuiti."""

import json

import click

from .orchestrator import Orchestrator
from .trading import TradingWorkflow


@click.group()
@click.pass_context
def main(ctx: click.Context) -> None:
    """智慧体 (zhihuiti) — autonomous multi-agent orchestration."""
    ctx.ensure_object(dict)
    ctx.obj["orchestrator"] = Orchestrator()


@main.command()
@click.argument("goal")
@click.option("--rounds", "-r", default=10, help="Max rounds")
@click.pass_context
def run(ctx: click.Context, goal: str, rounds: int) -> None:
    """Run a goal through the orchestration pipeline."""
    orch = ctx.obj["orchestrator"]
    orch.run(goal, max_rounds=rounds)


@main.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show system status."""
    orch = ctx.obj["orchestrator"]
    s = orch.status()
    click.echo("\n智慧体 System Status")
    click.echo("=" * 40)
    click.echo(f"\nAgents: {s['agents']['alive']} alive / {s['agents']['total']} total")
    for realm, count in s["agents"]["by_realm"].items():
        click.echo(f"  {realm}: {count}")
    click.echo(f"\nTasks: {s['tasks']['completed']} done / {s['tasks']['failed']} failed / {s['tasks']['pending']} pending")
    click.echo(f"\nEconomy:")
    for k, v in s["economy"].items():
        click.echo(f"  {k}: {v:.1f}")


@main.command()
@click.pass_context
def agents(ctx: click.Context) -> None:
    """List alive agents with realm info."""
    orch = ctx.obj["orchestrator"]
    alive = orch.memory.list_alive_agents()
    if not alive:
        click.echo("No alive agents.")
        return
    click.echo(f"\n{'Name':<15} {'Role':<12} {'Realm':<10} {'Tokens':<10} {'Score':<8} {'Tasks':<6}")
    click.echo("-" * 65)
    for a in alive:
        click.echo(
            f"{a.config.name:<15} {a.config.role:<12} {a.realm:<10} "
            f"{a.tokens:<10.1f} {a.average_score:<8.2f} {a.tasks_completed:<6}"
        )


@main.command()
@click.pass_context
def economy(ctx: click.Context) -> None:
    """Show economy metrics."""
    orch = ctx.obj["orchestrator"]
    metrics = orch.memory.get_all_economy()
    click.echo("\n智慧体 Economy")
    click.echo("=" * 30)
    for k, v in metrics.items():
        click.echo(f"  {k}: {v:,.1f}")


@main.command()
@click.pass_context
def history(ctx: click.Context) -> None:
    """Show task history."""
    orch = ctx.obj["orchestrator"]
    tasks = orch.memory.get_all_tasks()
    if not tasks:
        click.echo("No tasks yet.")
        return
    click.echo(f"\n{'ID':<10} {'Status':<12} {'Score':<8} {'Realm':<10} Description")
    click.echo("-" * 80)
    for t in tasks:
        click.echo(f"{t.task_id:<10} {t.status:<12} {t.score:<8.2f} {t.realm:<10} {t.description[:40]}")


@main.command()
@click.argument("ticker")
@click.option("--signals", "-s", default=5, help="Number of signals to discover")
@click.option("--top", "-t", default=3, help="Top N signals to generate Pine Script for")
@click.pass_context
def trade(ctx: click.Context, ticker: str, signals: int, top: int) -> None:
    """Run quantitative trading signal workflow for a ticker."""
    orch = ctx.obj["orchestrator"]
    workflow = TradingWorkflow(
        llm=orch.llm,
        memory=orch.memory,
        agents=orch.agents,
        reward_engine=orch.reward_engine,
        judge=orch.judge,
    )
    result = workflow.run(ticker.upper(), num_signals=signals, top_n=top)
    click.echo(f"\n✅ Found {len(result.signals)} signals for {result.ticker}")


@main.command()
@click.option("--port", "-p", default=8420, help="Port to serve on")
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to")
def dashboard(port: int, host: str) -> None:
    """Launch the web dashboard."""
    import uvicorn

    from .api import create_app

    click.echo(f"\n智慧体 Dashboard starting at http://{host}:{port}")
    click.echo("Press Ctrl+C to stop.\n")
    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level="warning")


@main.command()
@click.argument("agent_id")
@click.pass_context
def bloodline(ctx: click.Context, agent_id: str) -> None:
    """Trace 7-generation lineage for an agent."""
    orch = ctx.obj["orchestrator"]
    lineage = orch.bloodline.trace_lineage(agent_id)
    if not lineage:
        click.echo(f"No lineage found for {agent_id}.")
        return
    click.echo(f"\nLineage for {agent_id}:")
    for entry in lineage:
        click.echo(f"  Gen {entry['generation']}: {entry['child_id']} <- {entry['parent_ids']}")
        click.echo(f"    Traits: {json.dumps(entry['merged_traits'])}")


@main.command()
@click.pass_context
def loans(ctx: click.Context) -> None:
    """Show active loans between agents."""
    orch = ctx.obj["orchestrator"]
    active = orch.memory.get_loans(status="active")
    if not active:
        click.echo("No active loans.")
        return
    click.echo(f"\n{'ID':<10} {'Lender':<10} {'Borrower':<10} {'Principal':<10} {'Rate':<8} {'Repaid':<10} {'Due':<6}")
    click.echo("-" * 70)
    for l in active:
        click.echo(
            f"{l['loan_id']:<10} {l['lender_id']:<10} {l['borrower_id']:<10} "
            f"{l['principal']:<10.1f} {l['interest_rate']:<8.0%} "
            f"{l['amount_repaid']:<10.1f} {l['due_after_tasks']:<6}"
        )


@main.command()
@click.pass_context
def futures(ctx: click.Context) -> None:
    """Show futures contracts."""
    orch = ctx.obj["orchestrator"]
    all_futures = orch.memory.get_futures()
    if not all_futures:
        click.echo("No futures contracts.")
        return
    click.echo(f"\n{'ID':<10} {'Buyer':<10} {'Task':<10} {'Stake':<8} {'Pred':<8} {'Actual':<8} {'Status':<8}")
    click.echo("-" * 65)
    for f in all_futures:
        actual = f"{f['actual_score']:.2f}" if f['actual_score'] is not None else "-"
        click.echo(
            f"{f['future_id']:<10} {f['buyer_id']:<10} {f['task_id']:<10} "
            f"{f['stake']:<8.1f} {f['predicted_score']:<8.2f} {actual:<8} {f['status']:<8}"
        )


@main.command("rels")
@click.option("--agent", "-a", default=None, help="Filter by agent ID")
@click.pass_context
def relationships(ctx: click.Context, agent: str) -> None:
    """Show agent relationships."""
    orch = ctx.obj["orchestrator"]
    if agent:
        rels = orch.memory.get_relationships(agent)
    else:
        rels = orch.memory.get_all_relationships()
    if not rels:
        click.echo("No relationships.")
        return
    click.echo(f"\n{'Agent A':<10} {'Type':<12} {'Agent B':<10} {'Strength':<10}")
    click.echo("-" * 45)
    for r in rels:
        click.echo(f"{r['agent_a']:<10} {r['rel_type']:<12} {r['agent_b']:<10} {r['strength']:<10.2f}")


if __name__ == "__main__":
    main()
