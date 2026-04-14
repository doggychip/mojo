import { NextRequest, NextResponse } from 'next/server';

const BINANCE_BASE = 'https://api.binance.com/api/v3';

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const symbol = searchParams.get('symbol') || 'BTCUSDT';
  const interval = searchParams.get('interval') || '1h';
  const limit = searchParams.get('limit') || '24';
  const type = searchParams.get('type') || 'klines';

  try {
    if (type === 'price') {
      const res = await fetch(`${BINANCE_BASE}/ticker/price?symbol=${symbol}`);
      if (!res.ok) throw new Error(`Binance error: ${res.status}`);
      const data = await res.json();
      return NextResponse.json(data);
    }

    if (type === 'prices') {
      const res = await fetch(`${BINANCE_BASE}/ticker/price`);
      if (!res.ok) throw new Error(`Binance error: ${res.status}`);
      const all = await res.json();
      const symbols = symbol.split(',');
      const filtered = (all as { symbol: string; price: string }[]).filter((t) =>
        symbols.includes(t.symbol)
      );
      return NextResponse.json(filtered);
    }

    // Default: klines
    const url = `${BINANCE_BASE}/klines?symbol=${symbol}&interval=${interval}&limit=${limit}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Binance error: ${res.status}`);
    const raw: number[][] = await res.json();

    const klines = raw.map((k) => ({
      openTime: k[0],
      open: parseFloat(String(k[1])),
      high: parseFloat(String(k[2])),
      low: parseFloat(String(k[3])),
      close: parseFloat(String(k[4])),
      volume: parseFloat(String(k[5])),
      closeTime: k[6],
    }));

    return NextResponse.json(klines);
  } catch (err) {
    console.error('GET /api/market error:', err);
    return NextResponse.json({ error: 'Failed to fetch market data' }, { status: 500 });
  }
}
