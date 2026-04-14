# Mojo — Agentic Trading OS

> Speak a strategy → agent runs it 24/7.

Mojo is a paper-trading MVP that lets you describe crypto trading strategies in natural language. AI agents parse your intent, monitor real market data, and simulate execution — no real money, no wallet needed.

## Features

- **Ask Mojo chat** — describe any strategy in plain English, get a structured execution plan back
- **AI agent lifecycle** — create, run, pause, stop agents; each monitors its assigned asset 24/7
- **Real market data** — Binance REST API for prices + klines, WebSocket-like polling for the ticker bar
- **Paper trade logging** — every simulated buy/sell recorded with price, size, and reason
- **Mojo Signals** — RSI-based signals computed live for BTC, ETH, SOL, BNB, ADA
- **Portfolio view** — track all paper trades and unrealized P&L across all agents

## Stack

- Next.js 14 (App Router) + TypeScript + Tailwind CSS
- SQLite via `better-sqlite3`
- Anthropic Claude API (`claude-sonnet-4-20250514`)
- Binance public REST API (no API key required)

## Setup

```bash
git clone https://github.com/doggychip/mojo
cd mojo
npm install

# Add your Anthropic key
cp .env.example .env.local
# Edit .env.local and set ANTHROPIC_API_KEY

npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Usage

1. **Ask Mojo** tab → type a strategy like:
   - *"Buy ETH when RSI drops below 30, sell when it hits 70"*
   - *"Go long BTC if price drops 5% in 1 hour, take profit at 10%"*
   - *"Long SOL when volume spikes 2x above average"*

2. Review the parsed strategy card — check entry/exit conditions and risk controls.

3. Click **Launch Agent** → agent starts monitoring immediately.

4. Switch to **Agents** tab to see live logs, paper trades, and config.

5. **Signals** tab shows Mojo's RSI-based signals for top assets.

6. **Portfolio** tab shows aggregate paper trade P&L.

## Environment Variables

```
ANTHROPIC_API_KEY=sk-ant-...   # Required: Claude API key
```

Binance public API requires no authentication.

## Architecture

```
app/
  api/parse-strategy/   → Claude parses NL → structured JSON strategy
  api/agents/           → CRUD for agent records (SQLite)
  api/agents/[id]/      → Agent detail, status updates
  api/agent-runner/     → Ticks a running agent (fetches price, evaluates conditions)
  api/market/           → Binance API proxy

lib/
  agent-engine.ts       → Condition evaluators (RSI, price, volume)
  binance.ts            → Binance REST helpers + RSI/volume calculations
  db.ts                 → SQLite connection + schema init
  types.ts              → Shared TypeScript types

components/
  chat/MojoChat.tsx     → Main chat interface
  agents/AgentsView.tsx → Agent list + detail with live log
  signals/SignalsView.tsx → Live signals dashboard
  portfolio/            → Paper trade P&L tracker
```

## What's NOT in this MVP

- Real trade execution (no wallet, no signing, no real money)
- User authentication
- On-chain data, social monitoring
- Backtesting, strategy marketplace, push notifications

**Paper trading only. This is a demo — not financial advice.**
