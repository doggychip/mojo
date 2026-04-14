'use client';

import { ParsedStrategy } from '@/lib/types';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';

interface StrategyCardProps {
  strategy: ParsedStrategy;
  onConfirm: (strategy: ParsedStrategy) => void;
  onEdit: () => void;
  loading?: boolean;
}

export default function StrategyCard({ strategy, onConfirm, onEdit, loading }: StrategyCardProps) {
  const confidencePct = Math.round(strategy.confidence * 100);

  return (
    <div className="rounded-2xl border border-[#333] bg-[#141414] overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#333] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[#C8E64A] text-sm">⚡</span>
          <span className="font-semibold text-[#F5F5F5] text-sm">{strategy.name}</span>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={strategy.direction === 'long' ? 'green' : strategy.direction === 'short' ? 'red' : 'cyan'}>
            {strategy.direction}
          </Badge>
          <Badge variant="lime">{strategy.asset}</Badge>
        </div>
      </div>

      <div className="p-4 space-y-3">
        {/* Description */}
        <p className="text-[#AAAAAA] text-[13px]">{strategy.description}</p>

        {/* Confidence */}
        <div className="flex items-center gap-2">
          <span className="text-[#666] text-xs">Confidence</span>
          <div className="flex-1 h-1.5 bg-[#262626] rounded-full overflow-hidden">
            <div
              className="h-full rounded-full bg-[#C8E64A]"
              style={{ width: `${confidencePct}%` }}
            />
          </div>
          <span className="text-[#C8E64A] text-xs font-semibold">{confidencePct}%</span>
        </div>

        {/* Entry Conditions */}
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[#666] mb-1.5">Entry Conditions</p>
          <div className="space-y-1">
            {strategy.entry_conditions.map((c, i) => (
              <div key={i} className="flex items-start gap-2 text-[13px]">
                <span className="text-[#22C55E] mt-0.5">▲</span>
                <span className="text-[#AAAAAA]">{c.description}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Exit Conditions */}
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[#666] mb-1.5">Exit Conditions</p>
          <div className="space-y-1">
            {strategy.exit_conditions.map((c, i) => (
              <div key={i} className="flex items-start gap-2 text-[13px]">
                <span className="text-[#EF4444] mt-0.5">▼</span>
                <span className="text-[#AAAAAA]">{c.description}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Risk Controls */}
        <div className="rounded-xl bg-[#1E1E1E] p-3 grid grid-cols-3 gap-2">
          <div className="text-center">
            <p className="text-[10px] text-[#666] uppercase tracking-wide">Stop Loss</p>
            <p className="text-[#EF4444] font-semibold text-sm">{strategy.risk_controls.stop_loss_pct}%</p>
          </div>
          <div className="text-center">
            <p className="text-[10px] text-[#666] uppercase tracking-wide">Take Profit</p>
            <p className="text-[#22C55E] font-semibold text-sm">{strategy.risk_controls.take_profit_pct}%</p>
          </div>
          <div className="text-center">
            <p className="text-[10px] text-[#666] uppercase tracking-wide">Max Size</p>
            <p className="text-[#F5F5F5] font-semibold text-sm">${strategy.risk_controls.max_position_size_usd}</p>
          </div>
        </div>

        {/* Warnings */}
        {strategy.warnings && strategy.warnings.length > 0 && (
          <div className="rounded-xl bg-[rgba(245,158,11,0.08)] border border-[rgba(245,158,11,0.2)] p-3">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[#F59E0B] mb-1">Warnings</p>
            {strategy.warnings.map((w, i) => (
              <p key={i} className="text-[#F59E0B] text-[12px]">• {w}</p>
            ))}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2 pt-1">
          <Button variant="secondary" size="sm" onClick={onEdit} className="flex-1">
            Modify
          </Button>
          <Button variant="primary" size="sm" onClick={() => onConfirm(strategy)} loading={loading} className="flex-1">
            Launch Agent
          </Button>
        </div>
      </div>
    </div>
  );
}
