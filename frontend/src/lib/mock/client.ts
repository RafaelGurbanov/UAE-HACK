// Mock implementation of ApiClient. Same interface, local fixtures only.
// Scenario replay is scripted in Phase 3; the plumbing (subscribers, seq) is here.
import type { ApiClient } from '../client';
import type { AuditEntry, StreamEnvelope } from '../types';
import * as fx from './fixtures';

const wait = (ms: number, signal?: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    const t = setTimeout(resolve, ms);
    signal?.addEventListener('abort', () => {
      clearTimeout(t);
      reject(new DOMException('Aborted', 'AbortError'));
    });
  });
const later = async <T>(v: T, ms = 300): Promise<T> => {
  await wait(ms);
  return structuredClone(v);
};

const NO_SOURCE_PATTERN = /speed limit|weather|football|recipe|حدود السرعة/i;
const auditLog: AuditEntry[] = [...fx.mockAudit.entries];
const subscribers = new Map<string, Set<(e: StreamEnvelope) => void>>();
const runs = new Map<string, { scenarioId: string; released: number; seq: number }>();

function emit(runId: string, type: StreamEnvelope['type'], data: Record<string, unknown>) {
  const run = runs.get(runId);
  if (!run) return;
  const env: StreamEnvelope = {
    type,
    run_id: runId,
    seq: ++run.seq,
    ts: new Date().toISOString(),
    data,
  };
  subscribers.get(runId)?.forEach((fn) => fn(env));
}

function pushAudit(e: Omit<AuditEntry, 'audit_id' | 'timestamp'>): string {
  const audit_id = `aud_mock_${(auditLog.length + 1).toString().padStart(4, '0')}`;
  auditLog.unshift({ ...e, audit_id, timestamp: new Date().toISOString() });
  return audit_id;
}

export const mockClient: ApiClient = {
  mode: 'mock',
  health: () => later(fx.mockHealth),
  taxonomy: () => later(fx.mockTaxonomy, 50),
  sources: () => later(fx.mockSources),
  law: async (id) => {
    const law = fx.mockLaws[id];
    await wait(250);
    if (!law) throw Object.assign(new Error(`Unknown doc_id '${id}'`), { status: 404 });
    return structuredClone(law);
  },
  ask: async (body) =>
    later(NO_SOURCE_PATTERN.test(body.question) ? fx.mockNoSource : fx.mockAnswer, 700),
  async *askStream(body, signal) {
    if (body.mode === 'general') {
      const g = structuredClone(fx.mockGeneral);
      for (const w of g.answer!.short_answer.split(' ')) {
        await wait(30, signal);
        yield { type: 'token', data: { text: `${w} ` } };
      }
      g.audit_id = pushAudit({
        kind: 'ask',
        mode: 'general',
        outcome: 'general',
        agent: 'legal_adviser',
        run_id: null,
        input_event: body.question,
        retrieved_chunks: [],
        reasoning_steps: ['Mode general: no retrieval'],
        recommendation: null,
        citations: [],
        confidence: null,
        pipeline_nodes: [],
        readiness_dimensions: [],
        requires_human_decision: false,
        llm: { provider: 'mock' },
      });
      yield { type: 'final', data: g };
      return;
    }
    const refuse = NO_SOURCE_PATTERN.test(body.question);
    const final = structuredClone(refuse ? fx.mockNoSource : fx.mockAnswer);
    await wait(250, signal);
    yield {
      type: 'retrieval',
      data: {
        chunks: refuse
          ? []
          : final.answer!.legal_basis.map((c) => ({
              chunk_id: c.chunk_id,
              doc_id: c.doc_id,
              article: c.article,
              score: c.score,
            })),
      },
    };
    if (!refuse) {
      for (const w of final.answer!.short_answer.split(' ')) {
        await wait(35, signal);
        yield { type: 'token', data: { text: `${w} ` } };
      }
      yield { type: 'verification', data: final.verification };
    }
    final.audit_id = pushAudit({
      kind: 'ask',
      mode: 'grounded',
      outcome: final.outcome,
      agent: 'legal_adviser',
      run_id: null,
      input_event: body.question,
      retrieved_chunks: [],
      reasoning_steps: refuse
        ? ['Best score below threshold', 'Refused: no source']
        : ['Retrieved demo chunks', 'Verified 1/1 citations'],
      recommendation: null,
      citations: [],
      confidence: null,
      pipeline_nodes: final.pipeline_nodes,
      readiness_dimensions: final.readiness_dimensions,
      requires_human_decision: final.requires_human_decision,
      llm: { provider: 'mock' },
    });
    yield { type: 'final', data: final };
  },
  scenarios: () => later(fx.mockScenarios),
  async startScenario(id) {
    const scenario = fx.mockScenarios.find((s) => s.id === id);
    if (!scenario) throw new Error(`Unknown scenario '${id}'`);
    const run_id = `run_mock_${Date.now().toString(36)}`;
    runs.set(run_id, { scenarioId: id, released: 0, seq: 0 });
    await wait(150);
    queueMicrotask(() => emit(run_id, 'run_started', { scenario }));
    return { run_id, scenario, stream_url: '' };
  },
  async nextEvent(id, runId) {
    const run = runs.get(runId);
    const events = fx.mockScenarioEvents[id] ?? [];
    if (!run) throw new Error('Unknown run');
    const ev = events[run.released] ?? null;
    if (ev) {
      run.released += 1;
      emit(runId, 'event_released', { ...ev });
      emit(runId, 'pipeline_highlight', { nodes: ev.pipeline_nodes, severity: ev.severity });
      // Phase 3: scripted agent_status / agent_step / agent_assessment / coordinator replay
    }
    if (run.released >= events.length)
      emit(runId, 'run_completed', { summary: 'Demo run completed' });
    return { run_id: runId, released: ev, remaining: events.length - run.released };
  },
  subscribeScenario(_id, runId, onEvent) {
    if (!subscribers.has(runId)) subscribers.set(runId, new Set());
    subscribers.get(runId)!.add(onEvent);
    return () => subscribers.get(runId)?.delete(onEvent);
  },
  async reviewDecision(reviewId, d) {
    const audit_id = pushAudit({
      kind: 'human_decision',
      agent: null,
      run_id: null,
      input_event: reviewId,
      retrieved_chunks: [],
      reasoning_steps: [`${d.reviewer_role}: ${d.comment}`],
      recommendation: d.decision,
      citations: [],
      confidence: null,
      pipeline_nodes: ['P'],
      readiness_dimensions: ['human_interaction_supervision'],
      requires_human_decision: false,
      llm: null,
    });
    await wait(150);
    return { review_id: reviewId, decision: d.decision, audit_id };
  },
  gaps: () => later(fx.mockGaps),
  dataEntries: () => later({ entries: [], errors: [] }),
  dataEntry: async (id) => {
    throw Object.assign(new Error(`Unknown entry '${id}'`), { status: 404 });
  },
  audit: async (q = {}) => {
    const entries = auditLog.filter(
      (e) =>
        (!q.agent || e.agent === q.agent) &&
        (!q.run_id || e.run_id === q.run_id) &&
        (!q.kind || e.kind === q.kind) &&
        (!q.node || e.pipeline_nodes.includes(q.node)),
    );
    return later({ entries: entries.slice(0, q.limit ?? 200), total: entries.length }, 200);
  },
  exportAudit: async (format, runId) => {
    const e = auditLog.filter((x) => !runId || x.run_id === runId);
    return format === 'json'
      ? JSON.stringify(e, null, 2)
      : e.map((x) => JSON.stringify(x)).join('\n') + '\n';
  },
};
