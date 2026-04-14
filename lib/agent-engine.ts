import { ParsedStrategy, AgentLog, PaperTrade, EntryExitCondition } from './types';
import { getPrice, getKlines, calculateRSI, calculateVolumeSpike } from './binance';
import getDb from './db';

export interface TickResult {
  log_entry: Omit<AgentLog, 'id' | 'created_at'>;
  trade?: Omit<PaperTrade, 'id' | 'created_at'>;
}

async function evaluateCondition(
  condition: EntryExitCondition,
  currentPrice: number,
  symbol: string
): Promise<{ met: boolean; detail: string }> {
  const { type, params } = condition;

  switch (type) {
    case 'price_above': {
      const threshold = Number(params.price);
      return {
        met: currentPrice > threshold,
        detail: `Price ${currentPrice.toFixed(2)} ${currentPrice > threshold ? '>' : '<='} ${threshold}`,
      };
    }

    case 'price_below': {
      const threshold = Number(params.price);
      return {
        met: currentPrice < threshold,
        detail: `Price ${currentPrice.toFixed(2)} ${currentPrice < threshold ? '<' : '>='} ${threshold}`,
      };
    }

    case 'price_change_pct': {
      const lookbackMinutes = Number(params.lookback_minutes || 60);
      const targetPct = Number(params.change_pct);
      const intervals = Math.ceil(lookbackMinutes / 60);
      const klines = await getKlines(symbol, '1h', intervals + 2);
      if (klines.length < 2) return { met: false, detail: 'Insufficient data' };
      const pastPrice = klines[0].close;
      const actualPct = ((currentPrice - pastPrice) / pastPrice) * 100;
      const met = targetPct >= 0 ? actualPct >= targetPct : actualPct <= targetPct;
      return {
        met,
        detail: `${actualPct.toFixed(2)}% change vs target ${targetPct}%`,
      };
    }

    case 'volume_spike': {
      const klines = await getKlines(symbol, '1h', 24);
      const ratio = calculateVolumeSpike(klines);
      const threshold = Number(params.multiplier || 2);
      return {
        met: ratio >= threshold,
        detail: `Volume ${ratio.toFixed(2)}x avg (threshold: ${threshold}x)`,
      };
    }

    case 'rsi_above': {
      const klines = await getKlines(symbol, '1h', 30);
      const rsi = calculateRSI(klines);
      const threshold = Number(params.rsi);
      return {
        met: rsi > threshold,
        detail: `RSI ${rsi.toFixed(1)} ${rsi > threshold ? '>' : '<='} ${threshold}`,
      };
    }

    case 'rsi_below': {
      const klines = await getKlines(symbol, '1h', 30);
      const rsi = calculateRSI(klines);
      const threshold = Number(params.rsi);
      return {
        met: rsi < threshold,
        detail: `RSI ${rsi.toFixed(1)} ${rsi < threshold ? '<' : '>='} ${threshold}`,
      };
    }

    default:
      return { met: false, detail: `Unknown condition type: ${type}` };
  }
}

export async function tickAgent(
  agentId: string,
  strategy: ParsedStrategy
): Promise<TickResult> {
  const db = getDb();
  const symbol = strategy.asset;

  let currentPrice: number;
  try {
    currentPrice = await getPrice(symbol);
  } catch (err) {
    // Retry once
    try {
      currentPrice = await getPrice(symbol);
    } catch {
      const msg = `Failed to fetch price for ${symbol}: ${err}`;
      db.prepare(
        'INSERT INTO agent_logs (agent_id, event_type, message) VALUES (?, ?, ?)'
      ).run(agentId, 'error', msg);
      return {
        log_entry: { agent_id: agentId, event_type: 'error', message: msg, data: null },
      };
    }
  }

  // Evaluate all entry conditions
  const entryResults = await Promise.all(
    strategy.entry_conditions.map((c) => evaluateCondition(c, currentPrice, symbol))
  );
  const allEntryMet = entryResults.every((r) => r.met);

  // Evaluate all exit conditions
  const exitResults = await Promise.all(
    strategy.exit_conditions.map((c) => evaluateCondition(c, currentPrice, symbol))
  );
  const allExitMet = exitResults.every((r) => r.met);

  const conditionSummary = [
    'ENTRY:',
    ...strategy.entry_conditions.map((c, i) => `  [${entryResults[i].met ? '✓' : '✗'}] ${c.description}: ${entryResults[i].detail}`),
    'EXIT:',
    ...strategy.exit_conditions.map((c, i) => `  [${exitResults[i].met ? '✓' : '✗'}] ${c.description}: ${exitResults[i].detail}`),
  ].join('\n');

  const tickData = {
    price: currentPrice,
    symbol,
    entry_met: allEntryMet,
    exit_met: allExitMet,
    entry_results: entryResults,
    exit_results: exitResults,
  };

  let trade: Omit<PaperTrade, 'id' | 'created_at'> | undefined;

  if (allEntryMet && strategy.direction !== 'short') {
    // Would buy
    const positionUsd = strategy.risk_controls.max_position_size_usd;
    const quantity = positionUsd / currentPrice;
    const reason = `All entry conditions met at $${currentPrice.toFixed(2)}`;

    db.prepare(
      'INSERT INTO paper_trades (agent_id, side, asset, price, quantity, reason) VALUES (?, ?, ?, ?, ?, ?)'
    ).run(agentId, 'buy', symbol, currentPrice, quantity, reason);

    db.prepare(
      'INSERT INTO agent_logs (agent_id, event_type, message, data) VALUES (?, ?, ?, ?)'
    ).run(agentId, 'would_buy', `Would BUY ${quantity.toFixed(6)} ${symbol} @ $${currentPrice.toFixed(2)}`, JSON.stringify(tickData));

    trade = { agent_id: agentId, side: 'buy', asset: symbol, price: currentPrice, quantity, reason };
  } else if (allExitMet && strategy.direction !== 'short') {
    // Would sell
    const positionUsd = strategy.risk_controls.max_position_size_usd;
    const quantity = positionUsd / currentPrice;
    const reason = `All exit conditions met at $${currentPrice.toFixed(2)}`;

    db.prepare(
      'INSERT INTO paper_trades (agent_id, side, asset, price, quantity, reason) VALUES (?, ?, ?, ?, ?, ?)'
    ).run(agentId, 'sell', symbol, currentPrice, quantity, reason);

    db.prepare(
      'INSERT INTO agent_logs (agent_id, event_type, message, data) VALUES (?, ?, ?, ?)'
    ).run(agentId, 'would_sell', `Would SELL ${quantity.toFixed(6)} ${symbol} @ $${currentPrice.toFixed(2)}`, JSON.stringify(tickData));

    trade = { agent_id: agentId, side: 'sell', asset: symbol, price: currentPrice, quantity, reason: reason };
  } else {
    // Normal tick
    const msg = `Tick @ $${currentPrice.toFixed(2)} — no conditions met\n${conditionSummary}`;
    db.prepare(
      'INSERT INTO agent_logs (agent_id, event_type, message, data) VALUES (?, ?, ?, ?)'
    ).run(agentId, 'tick', msg, JSON.stringify(tickData));
  }

  const log: Omit<AgentLog, 'id' | 'created_at'> = {
    agent_id: agentId,
    event_type: trade ? (trade.side === 'buy' ? 'would_buy' : 'would_sell') : 'tick',
    message: trade
      ? `Would ${trade.side.toUpperCase()} ${trade.quantity.toFixed(6)} ${symbol} @ $${currentPrice.toFixed(2)}`
      : `Tick @ $${currentPrice.toFixed(2)} — monitoring`,
    data: tickData,
  };

  return { log_entry: log, trade };
}
