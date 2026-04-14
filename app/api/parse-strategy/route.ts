import { NextRequest, NextResponse } from 'next/server';
import Anthropic from '@anthropic-ai/sdk';

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const SYSTEM_PROMPT = `You are Mojo's strategy parser. Convert the user's natural language trading strategy into a structured JSON execution plan.

Return ONLY valid JSON with this schema:
{
  "name": "Short descriptive name for the agent",
  "description": "One-line summary of what the agent does",
  "asset": "BTCUSDT",
  "direction": "long",
  "entry_conditions": [
    {
      "type": "price_above",
      "params": { "price": 50000 },
      "description": "Human-readable description"
    }
  ],
  "exit_conditions": [
    {
      "type": "price_above",
      "params": { "price": 55000 },
      "description": "Human-readable description"
    }
  ],
  "risk_controls": {
    "max_position_size_usd": 1000,
    "stop_loss_pct": 5,
    "take_profit_pct": 10,
    "max_daily_trades": 3,
    "max_drawdown_pct": 10
  },
  "monitoring": {
    "data_sources": ["binance_price"],
    "check_interval_seconds": 30
  },
  "confidence": 0.8,
  "warnings": ["any risks or limitations"]
}

Supported condition types: price_above, price_below, price_change_pct, volume_spike, rsi_above, rsi_below, custom.

For price_change_pct params use: { "change_pct": number, "lookback_minutes": number }
For volume_spike params use: { "multiplier": number }
For rsi_above/rsi_below params use: { "rsi": number }
For price_above/price_below params use: { "price": number }

If the user's intent is ambiguous, fill in reasonable defaults for a conservative retail trader and note assumptions in warnings. Always include risk controls.`;

export async function POST(req: NextRequest) {
  try {
    const { prompt, conversation_history = [] } = await req.json();

    if (!prompt || typeof prompt !== 'string') {
      return NextResponse.json({ error: 'prompt is required' }, { status: 400 });
    }

    const messages: Array<{ role: 'user' | 'assistant'; content: string }> = [
      ...conversation_history,
      { role: 'user', content: prompt },
    ];

    const response = await client.messages.create({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 2048,
      system: SYSTEM_PROMPT,
      messages,
    });

    const text = response.content[0].type === 'text' ? response.content[0].text : '';

    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      return NextResponse.json({ error: 'Failed to parse strategy from Claude response' }, { status: 500 });
    }

    const strategy = JSON.parse(jsonMatch[0]);
    const reasoning = text.slice(0, jsonMatch.index).trim() || 'Strategy parsed successfully.';

    return NextResponse.json({ strategy, reasoning });
  } catch (err) {
    console.error('parse-strategy error:', err);
    return NextResponse.json(
      { error: err instanceof Error ? err.message : 'Internal error' },
      { status: 500 }
    );
  }
}
