'use client';

type Tab = 'chat' | 'agents' | 'signals' | 'portfolio';

interface BottomNavProps {
  active: Tab;
  onChange: (tab: Tab) => void;
  agentCount?: number;
}

const tabs: { id: Tab; label: string; icon: string }[] = [
  { id: 'chat', label: 'Ask Mojo', icon: '💬' },
  { id: 'agents', label: 'Agents', icon: '🤖' },
  { id: 'signals', label: 'Signals', icon: '📡' },
  { id: 'portfolio', label: 'Portfolio', icon: '📊' },
];

export default function BottomNav({ active, onChange, agentCount }: BottomNavProps) {
  return (
    <nav className="flex border-t border-[#333] bg-[#0A0A0A]">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={`flex-1 flex flex-col items-center gap-1 py-3 transition-colors relative ${
            active === tab.id ? 'text-[#C8E64A]' : 'text-[#444]'
          }`}
        >
          <span className="text-lg leading-none">{tab.icon}</span>
          <span className="text-[10px] font-semibold tracking-wide">{tab.label}</span>
          {tab.id === 'agents' && agentCount && agentCount > 0 ? (
            <span className="absolute top-2 right-1/4 w-4 h-4 rounded-full bg-[#C8E64A] text-[#0A0A0A] text-[9px] font-bold flex items-center justify-center">
              {agentCount}
            </span>
          ) : null}
        </button>
      ))}
    </nav>
  );
}
