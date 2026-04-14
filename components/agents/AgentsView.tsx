'use client';

import { useEffect, useState } from 'react';
import { Agent } from '@/lib/types';
import Badge from '@/components/ui/Badge';
import StatusDot from '@/components/ui/StatusDot';
import AgentDetail from './AgentDetail';

export default function AgentsView() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  async function fetchAgents() {
    try {
      const res = await fetch('/api/agents');
      if (res.ok) setAgents(await res.json());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchAgents();
    const interval = setInterval(fetchAgents, 10000);
    return () => clearInterval(interval);
  }, []);

  if (selectedId) {
    return <AgentDetail agentId={selectedId} onBack={() => setSelectedId(null)} />;
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-[#C8E64A] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-[#333] flex items-center justify-between">
        <h2 className="font-bold text-[#F5F5F5]">Agents</h2>
        <Badge variant="gray">{agents.filter((a) => a.status === 'running').length} running</Badge>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {agents.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-[#444] text-4xl mb-3">🤖</p>
            <p className="text-[#666] text-sm">No agents yet.</p>
            <p className="text-[#444] text-xs mt-1">Go to Ask Mojo and describe a trading strategy.</p>
          </div>
        ) : (
          agents.map((agent) => (
            <div
              key={agent.id}
              onClick={() => setSelectedId(agent.id)}
              className="rounded-2xl border border-[#333] bg-[#141414] p-4 cursor-pointer hover:border-[#444] transition-colors"
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="flex items-center gap-2 min-w-0">
                  <StatusDot status={agent.status} />
                  <p className="font-semibold text-[#F5F5F5] text-sm truncate">{agent.name}</p>
                </div>
                <div className="flex gap-1.5 flex-shrink-0">
                  <Badge variant={agent.parsed_strategy.direction === 'long' ? 'green' : agent.parsed_strategy.direction === 'short' ? 'red' : 'cyan'}>
                    {agent.parsed_strategy.direction}
                  </Badge>
                  <Badge variant="lime">{agent.parsed_strategy.asset}</Badge>
                </div>
              </div>

              <p className="text-[#666] text-[12px] mb-3 truncate">{agent.parsed_strategy.description}</p>

              {/* Latest log */}
              {agent.latest_log && (
                <div className="rounded-lg bg-[#1E1E1E] px-3 py-2">
                  <p className="text-[#AAAAAA] text-[11px] truncate font-mono">{agent.latest_log.message}</p>
                </div>
              )}

              <div className="flex items-center justify-between mt-2">
                <span className="text-[#444] text-[11px]">
                  {new Date(agent.created_at).toLocaleDateString()}
                </span>
                <span className="text-[#C8E64A] text-[11px]">View →</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
