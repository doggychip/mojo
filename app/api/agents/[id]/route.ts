import { NextRequest, NextResponse } from 'next/server';
import getDb from '@/lib/db';

export async function GET(_req: NextRequest, { params }: { params: { id: string } }) {
  try {
    const db = getDb();
    const agent = db.prepare('SELECT * FROM agents WHERE id = ?').get(params.id) as Record<string, unknown> | undefined;

    if (!agent) {
      return NextResponse.json({ error: 'Agent not found' }, { status: 404 });
    }

    const logs = db.prepare(
      'SELECT * FROM agent_logs WHERE agent_id = ? ORDER BY created_at DESC LIMIT 100'
    ).all(params.id);

    const trades = db.prepare(
      'SELECT * FROM paper_trades WHERE agent_id = ? ORDER BY created_at DESC LIMIT 50'
    ).all(params.id);

    return NextResponse.json({
      ...agent,
      parsed_strategy: JSON.parse(agent.parsed_strategy as string),
      config: agent.config ? JSON.parse(agent.config as string) : null,
      logs: (logs as Record<string, unknown>[]).map((l) => ({
        ...l,
        data: l.data ? JSON.parse(l.data as string) : null,
      })),
      trades,
    });
  } catch (err) {
    console.error('GET /api/agents/[id] error:', err);
    return NextResponse.json({ error: 'Failed to fetch agent' }, { status: 500 });
  }
}

export async function PATCH(req: NextRequest, { params }: { params: { id: string } }) {
  try {
    const { status } = await req.json();

    const validStatuses = ['pending', 'running', 'paused', 'stopped'];
    if (!validStatuses.includes(status)) {
      return NextResponse.json({ error: 'Invalid status' }, { status: 400 });
    }

    const db = getDb();
    const result = db.prepare(
      "UPDATE agents SET status = ?, updated_at = datetime('now') WHERE id = ?"
    ).run(status, params.id);

    if (result.changes === 0) {
      return NextResponse.json({ error: 'Agent not found' }, { status: 404 });
    }

    db.prepare(
      'INSERT INTO agent_logs (agent_id, event_type, message) VALUES (?, ?, ?)'
    ).run(params.id, 'info', `Status changed to ${status}`);

    const agent = db.prepare('SELECT * FROM agents WHERE id = ?').get(params.id) as Record<string, unknown>;
    return NextResponse.json({
      ...agent,
      parsed_strategy: JSON.parse(agent.parsed_strategy as string),
      config: agent.config ? JSON.parse(agent.config as string) : null,
    });
  } catch (err) {
    console.error('PATCH /api/agents/[id] error:', err);
    return NextResponse.json({ error: 'Failed to update agent' }, { status: 500 });
  }
}

export async function DELETE(_req: NextRequest, { params }: { params: { id: string } }) {
  try {
    const db = getDb();
    db.prepare('DELETE FROM agent_logs WHERE agent_id = ?').run(params.id);
    db.prepare('DELETE FROM paper_trades WHERE agent_id = ?').run(params.id);
    const result = db.prepare('DELETE FROM agents WHERE id = ?').run(params.id);

    if (result.changes === 0) {
      return NextResponse.json({ error: 'Agent not found' }, { status: 404 });
    }

    return NextResponse.json({ success: true });
  } catch (err) {
    console.error('DELETE /api/agents/[id] error:', err);
    return NextResponse.json({ error: 'Failed to delete agent' }, { status: 500 });
  }
}
