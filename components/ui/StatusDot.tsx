'use client';

import { AgentStatus } from '@/lib/types';

const colors: Record<AgentStatus, string> = {
  running: 'bg-[#22C55E]',
  paused: 'bg-[#F59E0B]',
  stopped: 'bg-[#EF4444]',
  pending: 'bg-[#666666]',
};

export default function StatusDot({ status }: { status: AgentStatus }) {
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full ${colors[status]} ${status === 'running' ? 'animate-pulse' : ''}`}
    />
  );
}
