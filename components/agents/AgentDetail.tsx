'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Agent, AgentLog as AgentLogType, PaperTrade } from '@/lib/types';
import AgentLogView from './AgentLog';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import StatusDot from '@/components/ui/StatusDot';

interface AgentDetailProps {
  agentId: string;
  onBack: () => void;
}

interface FullAgent extends Agent {
  logs: AgentLogType[];
  trades: PaperTrade[];
}

export default function AgentDetail({ agentId, onBack }: AgentDetailProps) {
  const [agent, setAgent] = useState<FullAgent | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [tab, setTab] = useState<'log' | 'trades' | 'config'>('log');
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchAgent = useCallback(async () => {
    try {
      const res = await fetch(`/api/agents/${agentId}`);
      if (!res.ok) return;
      const data = await res.json();
      setAgent(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  const tick = useCallback(async () => {
    try {
      await fetch('/api/agent-runner', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: agentId }),
      });
      fetchAgent();
    } catch {
      // ignore
    }
  }, [agentId, fetchAgent]);

  useEffect(() => {
    fetchAgent();
  }, [fetchAgent]);

  useEffect(() => {
    if (!agent) return;

    // Poll for updates every 5s
    const pollInterval = setInterval(fetchAgent, 5000);

    // Tick agent if running
    if (agent.status === 'running') {
      const interval = (agent.parsed_strategy.monitoring.check_interval_seconds || 30) * 1000;
      intervalRef.current = setInterval(tick, Math.max(interval, 10000));
    }

    return () => {
      clearInterval(pollInterval);
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [agent, fetchAgent, tick]);

  async function handleStatusChange(status: 'running' | 'paused' | 'stopped') {
    setActionLoading(true);
    try {
      await fetch(`/api/agents/${agentId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });
      fetchAgent();
    } finally {
      setActionLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-[#C8E64A] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!agent) {
    return <div className="text-center py-16 text-[#666]">Agent not found.</div>;
  }

  const strategy = agent.parsed_strategy;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#333] flex items-center gap-3">
        <button onClick={onBack} className="text-[#666] hover:text-[#F5F5F5] transition-colors">
          ←
        </button>
        <StatusDot status={agent.status} />
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-[#F5F5F5] text-sm truncate">{agent.name}</p>
          <p className="text-[#666] text-xs">{strategy.asset} · {strategy.direction}</p>
        </div>
        <Badge variant="lime">{agent.trades.length} trades</Badge>
      </div>

      {/* Controls */}
      <div className="px-4 py-2.5 flex gap-2 border-b border-[#333]">
        {agent.status !== 'running' && (
          <Button
            variant="primary"
            size="sm"
            loading={actionLoading}
            onClick={() => handleStatusChange('running')}
          >
            ▶ Run
          </Button>
        )}
        {agent.status === 'running' && (
          <Button
            variant="secondary"
            size="sm"
            loading={actionLoading}
            onClick={() => handleStatusChange('paused')}
          >
            ⏸ Pause
          </Button>
        )}
        {agent.status !== 'stopped' && (
          <Button
            variant="danger"
            size="sm"
            loading={actionLoading}
            onClick={() => handleStatusChange('stopped')}
          >
            ■ Stop
          </Button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#333]">
        {(['log', 'trades', 'config'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 py-2.5 text-xs font-semibold uppercase tracking-wide transition-colors ${
              tab === t ? 'text-[#C8E64A] border-b-2 border-[#C8E64A]' : 'text-[#666]'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {tab === 'log' && <AgentLogView logs={agent.logs} />}

        {tab === 'trades' && (
          <div className="space-y-2">
            {agent.trades.length === 0 ? (
              <div className="text-center py-8 text-[#444] text-sm">
                No paper trades yet. Agent is monitoring conditions...
              </div>
            ) : (
              agent.trades.map((t) => (
                <div key={t.id} className="rounded-xl bg-[#141414] border border-[#333] p-3">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-bold ${t.side === 'buy' ? 'text-[#22C55E]' : 'text-[#EF4444]'}`}>
                        {t.side === 'buy' ? '▲ BUY' : '▼ SELL'}
                      </span>
                      <span className="text-[#F5F5F5] text-xs font-semibold">{t.asset}</span>
                    </div>
                    <span className="text-[#F5F5F5] text-sm font-semibold">
                      ${t.price.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[#666] text-xs">{t.quantity.toFixed(6)} units</span>
                    <span className="text-[#666] text-xs">
                      {new Date(t.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                  {t.reason && <p className="text-[#AAAAAA] text-[11px] mt-1">{t.reason}</p>}
                </div>
              ))
            )}
          </div>
        )}

        {tab === 'config' && (
          <div className="space-y-4">
            <div>
              <p className="text-[10px] text-[#666] uppercase tracking-wide mb-2">Strategy</p>
              <p className="text-[#AAAAAA] text-sm">{strategy.description}</p>
            </div>
            <div>
              <p className="text-[10px] text-[#666] uppercase tracking-wide mb-2">Entry Conditions</p>
              {strategy.entry_conditions.map((c, i) => (
                <p key={i} className="text-[#AAAAAA] text-[13px]">• {c.description}</p>
              ))}
            </div>
            <div>
              <p className="text-[10px] text-[#666] uppercase tracking-wide mb-2">Exit Conditions</p>
              {strategy.exit_conditions.map((c, i) => (
                <p key={i} className="text-[#AAAAAA] text-[13px]">• {c.description}</p>
              ))}
            </div>
            <div>
              <p className="text-[10px] text-[#666] uppercase tracking-wide mb-2">Risk Controls</p>
              <div className="rounded-xl bg-[#141414] border border-[#333] p-3 space-y-2">
                {Object.entries(strategy.risk_controls).map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-[#666] text-xs">{k.replace(/_/g, ' ')}</span>
                    <span className="text-[#F5F5F5] text-xs font-semibold">
                      {typeof v === 'number' ? (k.includes('usd') ? `$${v}` : `${v}${k.includes('pct') ? '%' : ''}`) : v}
                    </span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <p className="text-[10px] text-[#666] uppercase tracking-wide mb-1">Original Prompt</p>
              <p className="text-[#AAAAAA] text-[13px] italic">&quot;{agent.user_prompt}&quot;</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
