'use client';

import { useState } from 'react';
import BottomNav from './BottomNav';
import TickerBar from './TickerBar';
import MojoChat from '@/components/chat/MojoChat';
import AgentsView from '@/components/agents/AgentsView';
import SignalsView from '@/components/signals/SignalsView';
import PortfolioView from '@/components/portfolio/PortfolioView';

type Tab = 'chat' | 'agents' | 'signals' | 'portfolio';

export default function AppShell() {
  const [activeTab, setActiveTab] = useState<Tab>('chat');
  const [agentCount, setAgentCount] = useState(0);

  return (
    <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center">
      {/* Phone frame on desktop, full-width on mobile */}
      <div className="w-full max-w-[430px] h-screen md:h-[812px] md:rounded-3xl md:shadow-2xl md:border md:border-[#333] bg-[#0A0A0A] flex flex-col overflow-hidden relative">
        {/* Paper Trading Banner */}
        <div className="flex items-center justify-center gap-2 py-1.5 bg-[rgba(200,230,74,0.08)] border-b border-[rgba(200,230,74,0.15)]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#C8E64A] animate-pulse" />
          <span className="text-[#C8E64A] text-[10px] font-semibold tracking-wide">
            PAPER TRADING MODE · NO REAL MONEY
          </span>
        </div>

        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#333]">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-xl bg-[#C8E64A] flex items-center justify-center">
              <span className="text-[#0A0A0A] font-black text-xs">M</span>
            </div>
            <span className="font-black text-[#F5F5F5] tracking-tight">mojo</span>
          </div>
          <span className="text-[#444] text-[11px]">Agentic Trading OS</span>
        </div>

        {/* Ticker */}
        <TickerBar />

        {/* Main content */}
        <div className="flex-1 overflow-hidden">
          <div className={activeTab === 'chat' ? 'h-full flex flex-col' : 'hidden'}>
            <MojoChat onAgentLaunched={() => setAgentCount((n) => n + 1)} />
          </div>
          <div className={activeTab === 'agents' ? 'h-full flex flex-col' : 'hidden'}>
            <AgentsView />
          </div>
          <div className={activeTab === 'signals' ? 'h-full flex flex-col' : 'hidden'}>
            <SignalsView />
          </div>
          <div className={activeTab === 'portfolio' ? 'h-full flex flex-col' : 'hidden'}>
            <PortfolioView />
          </div>
        </div>

        {/* Bottom nav */}
        <BottomNav active={activeTab} onChange={setActiveTab} agentCount={agentCount} />
      </div>
    </div>
  );
}
