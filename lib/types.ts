export type AgentStatus = 'pending' | 'running' | 'paused' | 'stopped';
export type LogEventType = 'tick' | 'signal' | 'would_buy' | 'would_sell' | 'error' | 'info';
export type TradeSide = 'buy' | 'sell';

export interface EntryExitCondition {
  type: 'price_above' | 'price_below' | 'price_change_pct' | 'volume_spike' | 'rsi_above' | 'rsi_below' | 'custom';
  params: Record<string, number | string>;
  description: string;
}

export interface RiskControls {
  max_position_size_usd: number;
  stop_loss_pct: number;
  take_profit_pct: number;
  max_daily_trades: number;
  max_drawdown_pct: number;
}

export interface Monitoring {
  data_sources: string[];
  check_interval_seconds: number;
}

export interface ParsedStrategy {
  name: string;
  description: string;
  asset: string;
  direction: 'long' | 'short' | 'both';
  entry_conditions: EntryExitCondition[];
  exit_conditions: EntryExitCondition[];
  risk_controls: RiskControls;
  monitoring: Monitoring;
  confidence: number;
  warnings: string[];
}

export interface Agent {
  id: string;
  name: string;
  status: AgentStatus;
  user_prompt: string;
  parsed_strategy: ParsedStrategy;
  config: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  latest_log?: AgentLog;
}

export interface AgentLog {
  id: number;
  agent_id: string;
  event_type: LogEventType;
  message: string;
  data: Record<string, unknown> | null;
  created_at: string;
}

export interface PaperTrade {
  id: number;
  agent_id: string;
  side: TradeSide;
  asset: string;
  price: number;
  quantity: number;
  reason: string | null;
  created_at: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  strategy?: ParsedStrategy;
  reasoning?: string;
}

export interface KlineData {
  openTime: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  closeTime: number;
}

export interface TickerPrice {
  symbol: string;
  price: string;
}
