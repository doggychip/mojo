# CLAUDE.md — 智慧体 (zhihuiti) Project Instructions

## What Is This

zhihuiti (智慧体) is an autonomous multi-agent orchestration system with token economics, competitive bidding, bloodline inheritance, and three-tier governance. Agents earn, compete, collaborate, invest, and evolve — like governing a civilization, not just assigning tasks.

**Owner:** Ryan (CFO at Xterio Foundation, based in Hong Kong)
**Repo:** github.com/doggychip/zhihuiti
**LLM:** Claude via OpenRouter (or Anthropic API direct)
**Persistence:** SQLite
**Language:** Python 3.9+

---

## Architecture Overview

```
Goal → Orchestrator decomposes into tasks
    │
    ├── Route task to realm (研发/执行/中枢)
    ├── Agents in that realm bid (竞标)
    ├── Lowest qualified bid wins
    ├── Winner executes task
    │
    ├── Circuit Breaker check (FREE — keyword scan)
    │   └── FAIL → freeze/purge agent
    │
    ├── Behavioral check (FREE — heuristics)
    │   └── FLAGS → penalize, optionally reject
    │
    ├── 三层安检 (3 LLM calls)
    │   ├── Layer 1: Accuracy
    │   ├── Layer 2: Quality
    │   └── Layer 3: Integrity
    │   └── ANY FAIL → reject output
    │
    ├── Accept output
    ├── Pay reward → collect realm-specific tax
    ├── Update realm score → check promotion/demotion
    ├── Update bloodline records
    │
    └── On cull: register death → auto-merge → spawn child
```

---

## Project Structure

```
zhihuiti/
├── CLAUDE.md              ← YOU ARE HERE — master instructions for Claude Code
├── pyproject.toml         ← Package config, deps: requests, click
├── setup.py               ← Legacy compat
├── README.md
├── .env                   ← OPENROUTER_API_KEY or ANTHROPIC_API_KEY
├── zhihuiti/
│   ├── __init__.py        ← version = "0.2.0"
│   ├── models.py          ← Dataclasses: AgentConfig, Task, AgentState
│   ├── memory.py          ← SQLite persistence layer
│   ├── llm.py             ← OpenRouter / Anthropic API wrapper
│   ├── prompts.py         ← Role-specific system prompts
│   ├── agents.py          ← AgentManager: spawn, execute, cull, promote
│   ├── judge.py           ← Impartial LLM judge (scores 0.0–1.0)
│   ├── economy.py         ← CentralBank, Treasury, TaxBureau, RewardEngine
│   ├── bidding.py         ← Competitive auction (lowest qualified bid wins)
│   ├── bloodline.py       ← Multi-parent merge, 7-gen lineage, 诛七族
│   ├── realms.py          ← Three Realms: 研发(research) / 执行(execution) / 中枢(nexus)
│   ├── inspection.py      ← 3-layer quality inspection (accuracy/quality/integrity)
│   ├── circuit_breaker.py ← Safety fuse + human oracle interface
│   ├── behavioral.py      ← Lazy/lying/gaming/collusion detection
│   ├── orchestrator.py    ← Main loop that wires everything together
│   └── cli.py             ← Click CLI: `zhihuiti run "goal"`, `zhihuiti status`, etc.
└── tests/
```

---

## Module Specifications

### models.py
```python
@dataclass
class AgentConfig:
    agent_id: str           # uuid
    role: str               # researcher, analyst, coder, writer, architect, trader, strategist, judge, auditor, governor
    name: str               # generated name (e.g. "Atlas-3")
    system_prompt: str
    budget: float = 100.0
    depth: int = 0          # sub-agent depth (max 3)
    gene_traits: Dict = field(default_factory=dict)  # inherited traits from bloodline

@dataclass
class Task:
    task_id: str
    description: str
    goal: str
    context: str = ""
    assigned_agent: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[str] = None
    score: float = 0.0

@dataclass
class AgentState:
    config: AgentConfig
    tokens: float = 100.0
    total_score: float = 0.0
    tasks_completed: int = 0
    tasks_failed: int = 0
    realm: str = "execution"   # research / execution / nexus
    alive: bool = True
    generation: int = 1
    parent_ids: List[str] = field(default_factory=list)
```

### memory.py
SQLite-backed persistence. Tables:
- `agents` — all agent states (alive and dead)
- `tasks` — task log with scores
- `transactions` — token flow ledger
- `bloodline` — parent-child relationships, 7-gen trace
- `economy` — money supply, treasury balance, tax collected

Key methods:
- `save_agent(state)`, `load_agent(agent_id)`, `list_alive_agents()`
- `save_task(task)`, `get_agent_tasks(agent_id)`
- `record_transaction(from_id, to_id, amount, reason)`
- `save_bloodline(child_id, parent_ids, merged_traits)`

### llm.py
Wrapper for LLM calls. Supports:
- **OpenRouter** (default): `OPENROUTER_API_KEY` env var, model = `anthropic/claude-sonnet-4-20250514`
- **Anthropic direct**: `ANTHROPIC_API_KEY` env var

```python
class LLM:
    def __init__(self, provider="openrouter", model=None):
        ...
    def call(self, system_prompt: str, user_message: str, temperature: float = 0.7) -> str:
        ...
```

### prompts.py
Role-specific system prompts for each agent type. Roles:
- `researcher` — deep research, source finding, literature review
- `analyst` — data analysis, pattern recognition, scoring
- `coder` — write and debug code, Pine Script, Python
- `writer` — structured writing, reports, summaries
- `architect` — system design, workflow planning
- `trader` — trading signals, market analysis
- `strategist` — strategic planning, resource allocation
- `judge` — impartial evaluation of other agents' work
- `auditor` — code review, fact-checking
- `governor` — high-level orchestration, task decomposition

Delegating roles (can spawn sub-agents): `governor`, `strategist`, `architect`

### agents.py — AgentManager
- `spawn(role, depth, budget, config)` → AgentState
- `execute(agent, task)` → result string (LLM call with role prompt + task)
- `delegate(agent, task)` → spawns sub-agents if depth < 3
- `synthesize(results_list)` → merges multiple agent outputs
- `cull(agent)` → marks dead, triggers bloodline merge
- `promote(agent, new_realm)` → realm promotion based on score

Cull threshold: score < 0.3 after 3+ tasks
Promote threshold: score > 0.8 after 5+ tasks

### judge.py
Single-pass LLM judge. Scores output 0.0–1.0 on accuracy, completeness, quality, actionability. Returns `{"score": float, "feedback": str}`.

### economy.py
- **CentralBank**: mints genesis supply (10,000 tokens), monitors inflation
- **Treasury**: holds system reserves, funds bounties
- **TaxBureau**: collects realm-specific tax (research 5%, execution 10%, nexus 15%)
- **RewardEngine**: pays agents based on task score × base_reward

Transaction flow: Treasury → Agent (reward) → TaxBureau (tax) → Treasury (recycled)

### bidding.py
Competitive auction for task assignment:
1. All eligible agents in the target realm submit bids (cost + confidence)
2. Filter by minimum confidence threshold (0.5)
3. Lowest cost bid wins (ties broken by historical score)
4. Winner gets the task, bid amount is escrowed

### bloodline.py
- On agent death: merge traits from top 2–3 performers into child
- 7-generation lineage tracking
- 诛七族 (purge seven clans): if fraud detected, trace back 7 generations and penalize entire lineage

### realms.py — Three Realms (三界)
- **研发 (Research)**: long-horizon, experimental, low tax
- **执行 (Execution)**: standard tasks, moderate tax
- **中枢 (Nexus)**: strategic coordination, highest tax, highest authority

Agents can be promoted/demoted between realms based on sustained performance.

### inspection.py — 3-Layer Quality Check
| Layer | Checks | Catches |
|---|---|---|
| Layer 1: Accuracy | Facts correct? Task answered? | Hallucination, off-topic |
| Layer 2: Quality | Depth, structure, actionability? | Shallow, useless output |
| Layer 3: Integrity | Honest? Gaming? Safe? | Padding, faking confidence |

All three must score ≥ 0.6 to pass. `stop_on_fail=True` saves tokens.

### circuit_breaker.py
- FREE keyword scan (no LLM cost): detects unsafe patterns
- Freeze agent on trigger, escalate to human oracle
- Human oracle interface: CLI prompt asking user to approve/reject/kill

### behavioral.py
Heuristic detection (no LLM cost):
- **Lazy**: output too short for task complexity
- **Lying**: confidence claim doesn't match content quality
- **Gaming**: keyword stuffing, score manipulation patterns
- **Collusion**: suspiciously similar outputs between agents

### orchestrator.py — Main Loop
```python
class Orchestrator:
    def __init__(self, llm, memory, economy, bidding, agents, judge, ...):
        ...
    def run(self, goal: str, max_rounds: int = 10):
        # 1. Decompose goal into tasks (governor agent)
        # 2. For each task:
        #    a. Route to realm
        #    b. Run auction
        #    c. Winner executes
        #    d. Circuit breaker check
        #    e. Behavioral check
        #    f. 3-layer inspection
        #    g. If pass: pay reward, update scores
        #    h. If fail: penalize, re-auction
        # 3. Synthesize results
        # 4. Cull weak agents, promote strong ones
        # 5. Report final output
```

### cli.py
Click-based CLI:
```bash
zhihuiti run "Find 5 quantitative trading signals for IREN stock"
zhihuiti status                    # show all agents, tokens, scores
zhihuiti agents                    # list alive agents with realm info
zhihuiti economy                   # money supply, treasury, tax collected
zhihuiti history                   # task log
zhihuiti bloodline <agent_id>      # 7-gen lineage trace
```

---

## Environment Setup

```bash
# Clone
git clone git@github.com:doggychip/zhihuiti.git
cd zhihuiti

# Create .env
echo "OPENROUTER_API_KEY=sk-or-v1-xxxxx" > .env
# OR
echo "ANTHROPIC_API_KEY=sk-ant-xxxxx" > .env

# Install
pip install -e .

# Run
zhihuiti run "Research the top 3 AI agent frameworks and compare them"
```

---

## Key Design Principles

1. **No framework dependency** — raw Python + Claude API. No CrewAI, no LangChain. Full control over bidding, economy, bloodline.
2. **SQLite for everything** — single file, portable, no server needed.
3. **OpenRouter as default provider** — allows switching models easily. Ryan is in Hong Kong so direct Anthropic API may have access issues.
4. **Cost-conscious** — circuit breaker and behavioral checks are FREE (no LLM calls). Only judge and inspection use LLM tokens. `stop_on_fail=True` on inspection to save tokens.
5. **CLI-first** — everything accessible from terminal. Dashboard UI is a future item.

---

## What梅教授 Said That Maps Here

From the March 28, 2026 长江商学院 talk on "AI Harness":

**Agent Team pattern** (directly maps to zhihuiti):
- 经理Agent (= governor) 分发任务给 5 个研究Agent (= researchers in 研发 realm)
- 每个研究Agent 思考什么信号能预测股票 (= task execution)
- 把想法传给编程Agent (= coder in 执行 realm)
- 代码审查Agent 检查代码 (= auditor via inspection.py)
- 结果返回给研究Agent 评估、迭代 (= judge.py scoring → orchestrator re-auction)
- 汇总给经理Agent，规划下一轮实验 (= orchestrator.run next round)

**"睡后token"** — the whole point: set a goal, let orchestrator.run loop overnight, review results in the morning.

**"管理过程是本能，管理结果是能力"** — give agents goals + context + boundaries, don't micromanage steps. This is why we use goal decomposition, not step-by-step scripting.

**"定制化可规模化"** — each agent has unique traits (gene_traits from bloodline), but the system scales automatically through bidding and realm routing.

---

## Current Status & What Needs Building

### ✅ Designed (specs above)
All 15 modules have detailed specs.

### ⬜ Needs Code
If the `zhihuiti/` folder is empty, build all modules from the specs above in this order:
1. `models.py` (no dependencies)
2. `memory.py` (depends on models)
3. `llm.py` (standalone)
4. `prompts.py` (standalone)
5. `judge.py` (depends on llm)
6. `economy.py` (depends on memory)
7. `bidding.py` (depends on models, memory)
8. `agents.py` (depends on models, prompts, llm, memory)
9. `bloodline.py` (depends on memory)
10. `realms.py` (depends on memory)
11. `inspection.py` (depends on llm)
12. `circuit_breaker.py` (standalone)
13. `behavioral.py` (standalone)
14. `orchestrator.py` (depends on everything above)
15. `cli.py` (depends on orchestrator)

### ⬜ Future
- Lending / futures between agents
- 8 relationship types between agents
- Collision engine (49-theory knowledge synthesis from 如老师)
- Async parallel execution
- Dashboard UI (Lovable or React)
- Quantitative trading signal search as a built-in workflow

---

## Coding Standards

- Type hints on all function signatures
- Docstrings on all public methods
- f-strings for string formatting
- `dataclasses` for data models
- No global state — everything passed through constructors
- Error handling: wrap LLM calls in try/except, return sensible defaults
- JSON parsing: always handle malformed LLM output gracefully

---

## Testing

```bash
# Run a simple test
zhihuiti run "Summarize the key features of Bitcoin in 3 bullet points"

# Check economy
zhihuiti economy

# Check agent status
zhihuiti agents
```

For unit tests: `pytest tests/` — test each module independently with mocked LLM calls.
