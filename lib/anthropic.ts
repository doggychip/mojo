import Anthropic from '@anthropic-ai/sdk';

const client = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

export const STRATEGY_PARSER_SYSTEM_PROMPT = `You are Mojo's strategy parser. Convert the user's natural language trading strategy into a structured JSON execution plan.

Return ONLY valid JSON with this schema:
{
  "name": "Short descriptive name for the agent",
  "description": "One-line summary of what the agent does",
  "asset": "BTCUSDT" | "ETHUSDT" | "SOLUSDT" | etc (Binance trading pair),
  "direction": "long" | "short" | "both",
  "entry_conditions": [
    {
      "type": "price_above" | "price_below" | "price_change_pct" | "volume_spike" | "rsi_above" | "rsi_below" | "custom",
      "params": { ... },
      "description": "Human-readable description of this condition"
    }
  ],
  "exit_conditions": [
    { same structure as entry }
  ],
  "risk_controls": {
    "max_position_size_usd": number,
    "stop_loss_pct": number,
    "take_profit_pct": number,
    "max_daily_trades": number,
    "max_drawdown_pct": number
  },
  "monitoring": {
    "data_sources": ["binance_price", "binance_orderbook", "on_chain", "social"],
    "check_interval_seconds": number
  },
  "confidence": 0.0-1.0,
  "warnings": ["any risks or limitations the user should know about"]
}

If the user's intent is ambiguous, fill in reasonable defaults for a conservative retail trader and note the assumptions in warnings. Always include risk controls even if the user didn't specify them.`;

export async function parseStrategy(
  prompt: string,
  conversationHistory: Array<{ role: 'user' | 'assistant'; content: string }> = []
): Promise<{ strategy: object; reasoning: string }> {
  const messages: Array<{ role: 'user' | 'assistant'; content: string }> = [
    ...conversationHistory,
    { role: 'user', content: prompt },
  ];

  const response = await client.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 2048,
    system: STRATEGY_PARSER_SYSTEM_PROMPT,
    messages,
  });

  const text = response.content[0].type === 'text' ? response.content[0].text : '';

  // Extract JSON from response
  const jsonMatch = text.match(/\{[\s\S]*\}/);
  if (!jsonMatch) {
    throw new Error('No JSON found in Claude response');
  }

  const strategy = JSON.parse(jsonMatch[0]);
  const reasoning = text.replace(jsonMatch[0], '').trim();

  return { strategy, reasoning };
}

export default client;
