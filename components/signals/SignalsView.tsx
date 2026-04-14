'use client';

import { useEffect, useState } from 'react';
import Badge from '@/components/ui/Badge';
import MiniChart from '@/components/ui/MiniChart';

interface Signal {
  symbol: string;
  displayName: string;
  price: number;
  mojoScore: number;
  signal: 'BUY' | 'SELL' | 'HOLD';
  reason: string;
  klines: number[];
}

const ASSETS = [
  { symbol: 'BTCUSDT', name: 'Bitcoin' },
  { symbol: 'ETHUSDT', name: 'Ethereum' },
  { symbol: 'SOLUSDT', name: 'Solana' },
  { symbol: 'BNBUSDT', name: 'BNB' },
  { symbol: 'ADAUSDT', name: 'Cardano' },
];

function computeSignal(klines: number[], price: number): { score: number; signal: 'BUY' | 'SELL' | 'HOLD'; reason: string } {
  if (klines.length < 14) return { score: 50, signal: 'HOLD', reason: 'Insufficient data' };

  // Simple RSI
  const changes = klines.slice(1).map((v, i) => v - klines[i]);
  const gains = changes.map((c) => (c > 0 ? c : 0));
  const losses = changes.map((c) => (c < 0 ? -c : 0));
  const period = 14;
  const avgGain = gains.slice(-period).reduce((a, b) => a + b, 0) / period;
  const avgLoss = losses.slice(-period).reduce((a, b) => a + b, 0) / period;
  const rsi = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);

  // Price change
  const pctChange = ((price - klines[0]) / klines[0]) * 100;

  let score = 50;
  let signal: 'BUY' | 'SELL' | 'HOLD' = 'HOLD';
  let reason = 'Market neutral';

  if (rsi < 35) {
    score = 80;
    signal = 'BUY';
    reason = `RSI oversold at ${rsi.toFixed(0)} — potential reversal`;
  } else if (rsi > 65) {
    score = 25;
    signal = 'SELL';
    reason = `RSI overbought at ${rsi.toFixed(0)} — potential correction`;
  } else if (pctChange > 3) {
    score = 65;
    signal = 'HOLD';
    reason = `+${pctChange.toFixed(1)}% move — watching momentum`;
  } else if (pctChange < -3) {
    score = 40;
    signal = 'HOLD';
    reason = `${pctChange.toFixed(1)}% dip — looking for support`;
  } else {
    score = 50;
    reason = `RSI ${rsi.toFixed(0)}, price change ${pctChange.toFixed(1)}%`;
  }

  return { score, signal, reason };
}

export default function SignalsView() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);

  async function fetchSignals() {
    try {
      const results = await Promise.all(
        ASSETS.map(async ({ symbol, name }) => {
          const [priceRes, klinesRes] = await Promise.all([
            fetch(`/api/market?type=price&symbol=${symbol}`),
            fetch(`/api/market?symbol=${symbol}&interval=1h&limit=24`),
          ]);

          const priceData = await priceRes.json();
          const klinesData = await klinesRes.json();

          const price = parseFloat(priceData.price || '0');
          const klines: number[] = Array.isArray(klinesData)
            ? klinesData.map((k: { close: number }) => k.close)
            : [];

          const { score, signal, reason } = computeSignal(klines, price);

          return {
            symbol,
            displayName: name,
            price,
            mojoScore: score,
            signal,
            reason,
            klines: klines.slice(-12),
          };
        })
      );

      setSignals(results.sort((a, b) => b.mojoScore - a.mojoScore));
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchSignals();
    const interval = setInterval(fetchSignals, 60000);
    return () => clearInterval(interval);
  }, []);

  const scoreColor = (score: number) =>
    score >= 65 ? '#22C55E' : score <= 35 ? '#EF4444' : '#AAAAAA';

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-[#333] flex items-center justify-between">
        <h2 className="font-bold text-[#F5F5F5]">Mojo Signals</h2>
        <Badge variant="cyan">Live</Badge>
      </div>

      <div className="px-4 py-2 text-[11px] text-[#444]">
        AI-computed signals · Updated every 60s · Not financial advice
      </div>

      {loading ? (
        <div className="flex items-center justify-center flex-1">
          <div className="w-6 h-6 border-2 border-[#C8E64A] border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {signals.map((s) => (
            <div key={s.symbol} className="rounded-2xl border border-[#333] bg-[#141414] p-4">
              <div className="flex items-start justify-between gap-2 mb-3">
                <div>
                  <p className="font-bold text-[#F5F5F5] text-sm">{s.displayName}</p>
                  <p className="text-[#666] text-xs">{s.symbol.replace('USDT', '')} / USDT</p>
                </div>
                <div className="text-right">
                  <p className="font-bold text-[#F5F5F5] text-sm">
                    ${s.price.toLocaleString(undefined, { maximumFractionDigits: s.price > 100 ? 2 : 4 })}
                  </p>
                  <Badge
                    variant={s.signal === 'BUY' ? 'green' : s.signal === 'SELL' ? 'red' : 'gray'}
                    size="sm"
                  >
                    {s.signal}
                  </Badge>
                </div>
              </div>

              <div className="flex items-end justify-between gap-3">
                <div className="flex-1">
                  {/* Mojo Score */}
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-[10px] text-[#666] uppercase tracking-wide">Mojo Score</span>
                    <span
                      className="text-sm font-bold"
                      style={{ color: scoreColor(s.mojoScore) }}
                    >
                      {s.mojoScore}
                    </span>
                  </div>
                  <div className="h-1.5 bg-[#262626] rounded-full overflow-hidden mb-2">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${s.mojoScore}%`,
                        backgroundColor: scoreColor(s.mojoScore),
                      }}
                    />
                  </div>
                  <p className="text-[#666] text-[11px]">{s.reason}</p>
                </div>

                <MiniChart
                  data={s.klines}
                  positive={s.signal !== 'SELL'}
                  width={80}
                  height={36}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
