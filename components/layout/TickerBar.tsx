'use client';

import { useEffect, useRef, useState } from 'react';

interface TickerItem {
  symbol: string;
  price: string;
  change?: number;
}

const SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'ADAUSDT'];
const DISPLAY = { BTCUSDT: 'BTC', ETHUSDT: 'ETH', SOLUSDT: 'SOL', BNBUSDT: 'BNB', ADAUSDT: 'ADA' };

export default function TickerBar() {
  const [tickers, setTickers] = useState<TickerItem[]>([]);
  const prevPrices = useRef<Record<string, number>>({});

  useEffect(() => {
    async function fetchPrices() {
      try {
        const res = await fetch(`/api/market?type=prices&symbol=${SYMBOLS.join(',')}`);
        if (!res.ok) return;
        const data: { symbol: string; price: string }[] = await res.json();

        const updated = data.map((item) => {
          const prev = prevPrices.current[item.symbol];
          const curr = parseFloat(item.price);
          const change = prev ? ((curr - prev) / prev) * 100 : 0;
          prevPrices.current[item.symbol] = curr;
          return { ...item, change };
        });

        setTickers(updated);
      } catch {
        // ignore
      }
    }

    fetchPrices();
    const interval = setInterval(fetchPrices, 15000);
    return () => clearInterval(interval);
  }, []);

  if (tickers.length === 0) return null;

  return (
    <div className="overflow-hidden bg-[#141414] border-b border-[#333]">
      <div className="flex items-center gap-6 px-4 py-2 overflow-x-auto scrollbar-hide">
        {tickers.map((t) => (
          <div key={t.symbol} className="flex items-center gap-1.5 flex-shrink-0">
            <span className="text-[#666] text-[11px] font-semibold">
              {DISPLAY[t.symbol as keyof typeof DISPLAY] || t.symbol}
            </span>
            <span className="text-[#F5F5F5] text-[11px] font-mono">
              ${parseFloat(t.price).toLocaleString(undefined, { maximumFractionDigits: 2 })}
            </span>
            {t.change !== undefined && (
              <span
                className={`text-[10px] font-semibold ${
                  t.change >= 0 ? 'text-[#22C55E]' : 'text-[#EF4444]'
                }`}
              >
                {t.change >= 0 ? '+' : ''}{t.change.toFixed(2)}%
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
