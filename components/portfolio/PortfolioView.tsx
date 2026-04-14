'use client';

import { useEffect, useState } from 'react';
import { Agent, PaperTrade } from '@/lib/types';
import Badge from '@/components/ui/Badge';

interface PortfolioStats {
  totalTrades: number;
  totalBuys: number;
  totalSells: number;
  agents: Agent[];
  recentTrades: (PaperTrade & { agent_name: string })[];
}

export default function PortfolioView() {
  const [stats, setStats] = useState<PortfolioStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [prices, setPrices] = useState<Record<string, number>>({});

  async function fetchPortfolio() {
    try {
      const agentsRes = await fetch('/api/agents');
      if (!agentsRes.ok) return;
      const agents: Agent[] = await agentsRes.json();

      // Fetch trades for each agent
      const allTrades: (PaperTrade & { agent_name: string })[] = [];
      for (const agent of agents) {
        const res = await fetch(`/api/agents/${agent.id}`);
        if (!res.ok) continue;
        const detail = await res.json();
        const trades: PaperTrade[] = detail.trades || [];
        allTrades.push(...trades.map((t: PaperTrade) => ({ ...t, agent_name: agent.name })));
      }

      allTrades.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

      setStats({
        totalTrades: allTrades.length,
        totalBuys: allTrades.filter((t) => t.side === 'buy').length,
        totalSells: allTrades.filter((t) => t.side === 'sell').length,
        agents,
        recentTrades: allTrades.slice(0, 20),
      });

      // Fetch current prices for assets in trades
      const symbols = Array.from(new Set(allTrades.map((t) => t.asset)));
      if (symbols.length > 0) {
        const priceRes = await fetch(`/api/market?type=prices&symbol=${symbols.join(',')}`);
        if (priceRes.ok) {
          const priceData: { symbol: string; price: string }[] = await priceRes.json();
          const priceMap: Record<string, number> = {};
          for (const p of priceData) priceMap[p.symbol] = parseFloat(p.price);
          setPrices(priceMap);
        }
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchPortfolio();
    const interval = setInterval(fetchPortfolio, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-[#C8E64A] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!stats || stats.totalTrades === 0) {
    return (
      <div className="flex flex-col h-full">
        <div className="px-4 py-3 border-b border-[#333]">
          <h2 className="font-bold text-[#F5F5F5]">Portfolio</h2>
        </div>
        <div className="flex-1 flex items-center justify-center flex-col gap-3">
          <p className="text-4xl">📊</p>
          <p className="text-[#666] text-sm">No paper trades yet.</p>
          <p className="text-[#444] text-xs">Launch an agent and it will simulate trades here.</p>
        </div>
      </div>
    );
  }

  // Compute P&L per agent from matched buy/sell pairs
  const agentPnL: Record<string, { buys: PaperTrade[]; sells: PaperTrade[]; unrealized: number }> = {};
  for (const trade of stats.recentTrades) {
    if (!agentPnL[trade.agent_id]) agentPnL[trade.agent_id] = { buys: [], sells: [], unrealized: 0 };
    if (trade.side === 'buy') agentPnL[trade.agent_id].buys.push(trade);
    else agentPnL[trade.agent_id].sells.push(trade);
  }

  // For each buy without a matched sell, compute unrealized P&L using current price
  let totalUnrealized = 0;
  for (const [, pnl] of Object.entries(agentPnL)) {
    const unmatched = pnl.buys.slice(pnl.sells.length);
    for (const trade of unmatched) {
      const current = prices[trade.asset];
      if (current) {
        pnl.unrealized += (current - trade.price) * trade.quantity;
      }
    }
    totalUnrealized += pnl.unrealized;
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-[#333] flex items-center justify-between">
        <h2 className="font-bold text-[#F5F5F5]">Portfolio</h2>
        <Badge variant="lime">Paper Mode</Badge>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* Summary stats */}
        <div className="p-4 grid grid-cols-3 gap-3">
          <div className="rounded-xl bg-[#141414] border border-[#333] p-3 text-center">
            <p className="text-[10px] text-[#666] uppercase tracking-wide mb-1">Trades</p>
            <p className="text-[#F5F5F5] font-bold text-lg">{stats.totalTrades}</p>
          </div>
          <div className="rounded-xl bg-[#141414] border border-[#333] p-3 text-center">
            <p className="text-[10px] text-[#666] uppercase tracking-wide mb-1">Buys</p>
            <p className="text-[#22C55E] font-bold text-lg">{stats.totalBuys}</p>
          </div>
          <div className="rounded-xl bg-[#141414] border border-[#333] p-3 text-center">
            <p className="text-[10px] text-[#666] uppercase tracking-wide mb-1">Sells</p>
            <p className="text-[#EF4444] font-bold text-lg">{stats.totalSells}</p>
          </div>
        </div>

        {/* Unrealized P&L */}
        <div className="px-4 pb-3">
          <div className="rounded-xl bg-[#141414] border border-[#333] p-4 text-center">
            <p className="text-[10px] text-[#666] uppercase tracking-wide mb-1">Unrealized P&L (Paper)</p>
            <p
              className="text-2xl font-bold"
              style={{ color: totalUnrealized >= 0 ? '#22C55E' : '#EF4444' }}
            >
              {totalUnrealized >= 0 ? '+' : ''}${totalUnrealized.toFixed(2)}
            </p>
          </div>
        </div>

        {/* Recent activity */}
        <div className="px-4 pb-4">
          <p className="text-[10px] text-[#666] uppercase tracking-wide mb-3">Recent Activity</p>
          <div className="space-y-2">
            {stats.recentTrades.map((t) => (
              <div key={t.id} className="flex items-center gap-3 py-2 border-b border-[#1E1E1E] last:border-0">
                <div
                  className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold"
                  style={{
                    backgroundColor: t.side === 'buy' ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
                    color: t.side === 'buy' ? '#22C55E' : '#EF4444',
                  }}
                >
                  {t.side === 'buy' ? '▲' : '▼'}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[#F5F5F5] text-xs font-semibold">
                    {t.side.toUpperCase()} {t.asset.replace('USDT', '')}
                  </p>
                  <p className="text-[#666] text-[10px] truncate">{t.agent_name}</p>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-[#F5F5F5] text-xs font-mono">
                    ${t.price.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                  </p>
                  <p className="text-[#666] text-[10px]">
                    {new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
