'use client';

import { ChatMessage as ChatMessageType } from '@/lib/types';
import StrategyCard from './StrategyCard';
import { ParsedStrategy } from '@/lib/types';

interface ChatMessageProps {
  message: ChatMessageType;
  onConfirmStrategy?: (strategy: ParsedStrategy) => void;
  onEditStrategy?: () => void;
  launchLoading?: boolean;
}

export default function ChatMessage({
  message,
  onConfirmStrategy,
  onEditStrategy,
  launchLoading,
}: ChatMessageProps) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] bg-[#262626] text-[#F5F5F5] rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {/* Assistant text */}
      {message.content && (
        <div className="flex items-start gap-2">
          <div className="w-6 h-6 rounded-full bg-[#C8E64A] flex items-center justify-center flex-shrink-0 mt-0.5">
            <span className="text-[10px] font-bold text-[#0A0A0A]">M</span>
          </div>
          <div className="text-[#AAAAAA] text-sm leading-relaxed max-w-[90%]">
            {message.content}
          </div>
        </div>
      )}

      {/* Strategy card */}
      {message.strategy && onConfirmStrategy && onEditStrategy && (
        <div className="ml-8">
          <StrategyCard
            strategy={message.strategy}
            onConfirm={onConfirmStrategy}
            onEdit={onEditStrategy}
            loading={launchLoading}
          />
        </div>
      )}
    </div>
  );
}
