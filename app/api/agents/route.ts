import { NextRequest, NextResponse } from 'next/server';
import getDb from '@/lib/db';

export async function GET() {
  try {
    const db = getDb();
    const agents = db.prepare(`
      SELECT a.*,
        (SELECT json_object(
          'id', l.id, 'event_type', l.event_type, 'message', l.message, 'created_at', l.created_at
        ) FROM agent_logs l WHERE l.agent_id = a.id ORDER BY l.created_at DESC LIMIT 1) as latest_log
      FROM agents a
      ORDER BY a.created_at DESC
    `).all();

    const parsed = (agents as Record<string, unknown>[]).map((a) => ({
      ...a,
      parsed_strategy: JSON.parse(a.parsed_strategy as string),
      config: a.config ? JSON.parse(a.config as string) : null,
      latest_log: a.latest_log ? JSON.parse(a.latest_log as string) : null,
    }));

    return NextResponse.json(parsed);
  } catch (err) {
    console.error('GET /api/agents error:', err);
    return NextResponse.json({ error: 'Failed to fetch agents' }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const { user_prompt, parsed_strategy } = await req.json();

    if (!user_prompt || !parsed_strategy) {
      return NextResponse.json({ error: 'user_prompt and parsed_strategy are required' }, { status: 400 });
    }

    const db = getDb();
    const id = Math.random().toString(36).slice(2, 10);

    db.prepare(`
      INSERT INTO agents (id, name, status, user_prompt, parsed_strategy)
      VALUES (?, ?, 'pending', ?, ?)
    `).run(id, parsed_strategy.name || 'Unnamed Agent', user_prompt, JSON.stringify(parsed_strategy));

    db.prepare(`
      INSERT INTO agent_logs (agent_id, event_type, message)
      VALUES (?, 'info', ?)
    `).run(id, `Agent created from strategy: ${parsed_strategy.name}`);

    const agent = db.prepare('SELECT * FROM agents WHERE id = ?').get(id) as Record<string, unknown>;
    return NextResponse.json({
      ...agent,
      parsed_strategy: JSON.parse(agent.parsed_strategy as string),
      config: agent.config ? JSON.parse(agent.config as string) : null,
    }, { status: 201 });
  } catch (err) {
    console.error('POST /api/agents error:', err);
    return NextResponse.json({ error: 'Failed to create agent' }, { status: 500 });
  }
}
