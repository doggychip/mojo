import { NextRequest, NextResponse } from 'next/server';
import getDb from '@/lib/db';
import { tickAgent } from '@/lib/agent-engine';
import { ParsedStrategy } from '@/lib/types';

export async function POST(req: NextRequest) {
  try {
    const { agent_id } = await req.json();

    if (!agent_id) {
      return NextResponse.json({ error: 'agent_id is required' }, { status: 400 });
    }

    const db = getDb();
    const agent = db.prepare('SELECT * FROM agents WHERE id = ?').get(agent_id) as
      | { id: string; status: string; parsed_strategy: string }
      | undefined;

    if (!agent) {
      return NextResponse.json({ error: 'Agent not found' }, { status: 404 });
    }

    if (agent.status !== 'running') {
      return NextResponse.json({ error: 'Agent is not running' }, { status: 400 });
    }

    const strategy: ParsedStrategy = JSON.parse(agent.parsed_strategy);
    const result = await tickAgent(agent_id, strategy);

    return NextResponse.json(result);
  } catch (err) {
    console.error('POST /api/agent-runner error:', err);
    return NextResponse.json({ error: 'Agent runner failed' }, { status: 500 });
  }
}
