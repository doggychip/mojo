'use client';

import { useState, useRef, useEffect } from 'react';
import { ChatMessage as ChatMessageType, ParsedStrategy } from '@/lib/types';
import ChatMessage from './ChatMessage';

interface MojoChatProps {
  onAgentLaunched?: () => void;
}

const WELCOME_MSG: ChatMessageType = {
  role: 'assistant',
  content:
    "Hey, I'm Mojo 👋 Tell me your trading strategy in plain English and I'll build an agent to monitor and execute it 24/7 — paper trading, no real money.\n\nTry: \"Buy ETH when RSI drops below 30, sell when it hits 70\"",
};

export default function MojoChat({ onAgentLaunched }: MojoChatProps) {
  const [messages, setMessages] = useState<ChatMessageType[]>([WELCOME_MSG]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [launchLoading, setLaunchLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const conversationHistory = messages
    .filter((m) => m.role !== 'assistant' || !m.strategy)
    .map((m) => ({ role: m.role, content: m.content }));

  async function handleSend() {
    const text = input.trim();
    if (!text || loading) return;

    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setLoading(true);

    try {
      const res = await fetch('/api/parse-strategy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: text, conversation_history: conversationHistory }),
      });

      if (!res.ok) throw new Error('Failed to parse strategy');
      const { strategy, reasoning } = await res.json();

      const assistantMsg: ChatMessageType = {
        role: 'assistant',
        content: reasoning || "Here's the strategy I've built for you:",
        strategy,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: "Sorry, I couldn't parse that strategy. Try being more specific — e.g., \"Buy BTC when price drops 5% in 1 hour, sell at 10% profit.\"",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function handleLaunchAgent(strategy: ParsedStrategy) {
    setLaunchLoading(true);
    try {
      const userPrompt = messages.filter((m) => m.role === 'user').slice(-1)[0]?.content || '';
      const res = await fetch('/api/agents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_prompt: userPrompt, parsed_strategy: strategy }),
      });

      if (!res.ok) throw new Error('Failed to create agent');
      const agent = await res.json();

      // Start the agent running
      await fetch(`/api/agents/${agent.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'running' }),
      });

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `✅ Agent "${strategy.name}" is now live! It's monitoring ${strategy.asset} every ${strategy.monitoring.check_interval_seconds}s. Switch to the Agents tab to track it.`,
        },
      ]);
      onAgentLaunched?.();
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: "Failed to launch agent. Please try again." },
      ]);
    } finally {
      setLaunchLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const SUGGESTIONS = [
    'Buy ETH when RSI < 30',
    'Buy BTC dip 5% in 1h',
    'Long SOL volume spike 2x',
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 pb-2">
        {messages.map((msg, i) => (
          <ChatMessage
            key={i}
            message={msg}
            onConfirmStrategy={msg.strategy ? handleLaunchAgent : undefined}
            onEditStrategy={msg.strategy ? () => inputRef.current?.focus() : undefined}
            launchLoading={launchLoading}
          />
        ))}

        {loading && (
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-[#C8E64A] flex items-center justify-center flex-shrink-0">
              <span className="text-[10px] font-bold text-[#0A0A0A]">M</span>
            </div>
            <div className="flex gap-1">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="w-1.5 h-1.5 rounded-full bg-[#666] animate-bounce"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Suggestions (only on first interaction) */}
      {messages.length === 1 && (
        <div className="px-4 pb-2 flex gap-2 flex-wrap">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => setInput(s)}
              className="text-xs bg-[#1E1E1E] border border-[#333] text-[#AAAAAA] rounded-full px-3 py-1.5 hover:border-[#C8E64A] hover:text-[#C8E64A] transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="p-4 pt-2">
        <div className="flex items-end gap-2 bg-[#1E1E1E] border border-[#333] rounded-2xl px-4 py-3 focus-within:border-[#C8E64A] transition-colors">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe your trading strategy..."
            rows={1}
            className="flex-1 bg-transparent text-[#F5F5F5] placeholder-[#666] text-sm resize-none outline-none leading-relaxed max-h-32 overflow-y-auto"
            style={{ scrollbarWidth: 'none' }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="w-8 h-8 rounded-full bg-[#C8E64A] flex items-center justify-center flex-shrink-0 disabled:opacity-30 hover:bg-[#d4ec60] transition-colors"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M7 1L13 7L7 13M1 7H13" stroke="#0A0A0A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
        <p className="text-[10px] text-[#444] text-center mt-2">
          Paper trading only · No real money
        </p>
      </div>
    </div>
  );
}
