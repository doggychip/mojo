import { KlineData, TickerPrice } from './types';

const BINANCE_BASE = 'https://api.binance.com/api/v3';

// Simple in-memory cache for klines (1-minute TTL)
const klineCache: Map<string, { data: KlineData[]; ts: number }> = new Map();
const CACHE_TTL = 60_000;

export async function getPrice(symbol: string): Promise<number> {
  const res = await fetch(`${BINANCE_BASE}/ticker/price?symbol=${symbol}`, {
    next: { revalidate: 0 },
  });
  if (!res.ok) throw new Error(`Binance price fetch failed: ${res.status}`);
  const data: TickerPrice = await res.json();
  return parseFloat(data.price);
}

export async function getMultiplePrices(symbols: string[]): Promise<Record<string, number>> {
  const res = await fetch(`${BINANCE_BASE}/ticker/price`, {
    next: { revalidate: 0 },
  });
  if (!res.ok) throw new Error(`Binance prices fetch failed: ${res.status}`);
  const data: TickerPrice[] = await res.json();

  const symbolSet = new Set(symbols);
  const result: Record<string, number> = {};
  for (const item of data) {
    if (symbolSet.has(item.symbol)) {
      result[item.symbol] = parseFloat(item.price);
    }
  }
  return result;
}

export async function getKlines(
  symbol: string,
  interval: string = '1h',
  limit: number = 24
): Promise<KlineData[]> {
  const cacheKey = `${symbol}-${interval}-${limit}`;
  const cached = klineCache.get(cacheKey);
  if (cached && Date.now() - cached.ts < CACHE_TTL) {
    return cached.data;
  }

  const url = `${BINANCE_BASE}/klines?symbol=${symbol}&interval=${interval}&limit=${limit}`;
  const res = await fetch(url, { next: { revalidate: 0 } });
  if (!res.ok) throw new Error(`Binance klines fetch failed: ${res.status}`);

  const raw: number[][] = await res.json();
  const data: KlineData[] = raw.map((k) => ({
    openTime: k[0],
    open: parseFloat(String(k[1])),
    high: parseFloat(String(k[2])),
    low: parseFloat(String(k[3])),
    close: parseFloat(String(k[4])),
    volume: parseFloat(String(k[5])),
    closeTime: k[6],
  }));

  klineCache.set(cacheKey, { data, ts: Date.now() });
  return data;
}

export function calculateRSI(klines: KlineData[], period: number = 14): number {
  if (klines.length < period + 1) return 50;

  const closes = klines.map((k) => k.close);
  const changes = closes.slice(1).map((c, i) => c - closes[i]);

  const gains = changes.map((c) => (c > 0 ? c : 0));
  const losses = changes.map((c) => (c < 0 ? -c : 0));

  const avgGain = gains.slice(-period).reduce((a, b) => a + b, 0) / period;
  const avgLoss = losses.slice(-period).reduce((a, b) => a + b, 0) / period;

  if (avgLoss === 0) return 100;
  const rs = avgGain / avgLoss;
  return 100 - 100 / (1 + rs);
}

export function calculateVolumeSpike(klines: KlineData[], periods: number = 20): number {
  if (klines.length < 2) return 1;
  const recent = klines[klines.length - 1].volume;
  const avg =
    klines
      .slice(-periods - 1, -1)
      .reduce((a, b) => a + b.volume, 0) /
    Math.min(periods, klines.length - 1);
  return avg > 0 ? recent / avg : 1;
}

export const DEFAULT_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'ADAUSDT'];
