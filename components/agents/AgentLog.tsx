'use client';

import { AgentLog as AgentLogType } from '@/lib/types';

interface AgentLogProps {
  logs: AgentLogType[];
}

const eventColors: Record<string, string> = {
  tick: '#666666',
  signal: '#06B6D4',
  would_buy: '#22C55E',
  would_sell: '#EF4444',
  error: '#EF4444',
  info: '#AAAAAA',
};

const eventIcons: Record<string, string> = {
  tick: '◎',
  signal: '⚡',
  would_buy: '▲',
  would_sell: '▼',
  error: '✗',
  info: 'ℹ',
};

function formatTime(ts: string) {
  const d = new Date(ts);
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export default function AgentLogView({ logs }: AgentLogProps) {
  if (logs.length === 0) {
    return (
      <div className="text-center py-8 text-[#444] text-sm">
        No activity yet. Agent is starting up...
      </div>
    );
  }

  return (
    <div className="space-y-0.5 font-mono text-[12px]">
      {logs.map((log) => (
        <div key={log.id} className="flex items-start gap-2 py-1.5 border-b border-[#1E1E1E] last:border-0">
          <span
            className="flex-shrink-0 mt-0.5"
            style={{ color: eventColors[log.event_type] || '#666' }}
          >
            {eventIcons[log.event_type] || '·'}
          </span>
          <span className="text-[#444] flex-shrink-0">{formatTime(log.created_at)}</span>
          <span
            className="flex-1 leading-relaxed break-words"
            style={{ color: eventColors[log.event_type] || '#AAAAAA' }}
          >
            {log.message}
          </span>
        </div>
      ))}
    </div>
  );
}
