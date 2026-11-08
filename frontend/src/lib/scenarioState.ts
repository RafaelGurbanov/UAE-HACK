// Pure reducer for the scenario room: SSE envelopes in, view state out. Dedupes by seq.
import type {
  AgentAssessmentEvent,
  Conflict,
  CoordinatorEvent,
  PipelineNode,
  ScenarioAgent,
  ScenarioEvent,
  StreamEnvelope,
} from './types';

export const SCENARIO_AGENTS: ScenarioAgent[] = [
  'data_protection',
  'education',
  'consumer_protection',
  'ai_ethics',
];
export type AgentState = 'idle' | 'thinking' | 'done';
export type Severity = ScenarioEvent['severity'];

export interface AgentView {
  status: AgentState;
  /** ids of events this agent was shown (information asymmetry) */
  seen: string[];
  steps: string[];
  assessments: AgentAssessmentEvent[];
}
export interface ReviewView {
  review_id: string;
  event_id: string;
  summary: string;
  decision?: { decision: string; reviewer_role: string; comment: string; audit_id: string };
}
export interface ScenarioView {
  lastSeq: number;
  events: ScenarioEvent[];
  agents: Record<ScenarioAgent, AgentView>;
  coordinator: { status: AgentState; recs: CoordinatorEvent[] };
  conflicts: (Conflict & { event_id?: string })[];
  reviews: ReviewView[];
  highlight: { nodes: PipelineNode[]; severity: Severity | null };
  busy: boolean;
  completed: boolean;
  error: string | null;
}

export const emptyView = (): ScenarioView => ({
  lastSeq: 0,
  events: [],
  agents: Object.fromEntries(
    SCENARIO_AGENTS.map((a) => [a, { status: 'idle', seen: [], steps: [], assessments: [] }]),
  ) as unknown as Record<ScenarioAgent, AgentView>,
  coordinator: { status: 'idle', recs: [] },
  conflicts: [],
  reviews: [],
  highlight: { nodes: [], severity: null },
  busy: false,
  completed: false,
  error: null,
});

const RANK: Record<Severity, number> = { info: 0, warning: 1, critical: 2 };

/** Highest severity released so far: drives the blue > amber > red colour shift. */
export function maxSeverity(v: ScenarioView): Severity | null {
  return v.events.reduce<Severity | null>(
    (m, e) => (m === null || RANK[e.severity] > RANK[m] ? e.severity : m),
    null,
  );
}

export type Action =
  | { type: 'envelope'; env: StreamEnvelope }
  | { type: 'release' }
  | { type: 'reset' }
  | { type: 'fail'; message: string };

function isAgent(a: unknown): a is ScenarioAgent {
  return SCENARIO_AGENTS.includes(a as ScenarioAgent);
}

export function reduce(v: ScenarioView, action: Action): ScenarioView {
  if (action.type === 'reset') return emptyView();
  if (action.type === 'release') return { ...v, busy: true, error: null };
  if (action.type === 'fail') return { ...v, busy: false, error: action.message };
  const env = action.env;
  if (env.seq <= v.lastSeq) return v; // replayed / duplicate
  const d = env.data as Record<string, unknown>;
  const next: ScenarioView = { ...v, lastSeq: env.seq };
  const agentPatch = (a: ScenarioAgent, patch: (x: AgentView) => AgentView) => {
    next.agents = { ...next.agents, [a]: patch(next.agents[a]) };
  };
  switch (env.type) {
    case 'event_released': {
      const ev = d as unknown as ScenarioEvent;
      next.events = [...v.events, ev];
      next.busy = true;
      for (const a of ev.visible_to)
        if (isAgent(a)) agentPatch(a, (x) => ({ ...x, seen: [...x.seen, ev.id] }));
      break;
    }
    case 'pipeline_highlight':
      next.highlight = {
        nodes: (d.nodes as PipelineNode[]) ?? [],
        severity: (d.severity as Severity) ?? null,
      };
      break;
    case 'agent_status': {
      const st = d.state as AgentState;
      if (d.agent === 'coordinator') {
        next.coordinator = { ...v.coordinator, status: st };
        if (st === 'done') next.busy = false;
      } else if (isAgent(d.agent)) agentPatch(d.agent, (x) => ({ ...x, status: st }));
      break;
    }
    case 'agent_step':
      if (isAgent(d.agent))
        agentPatch(d.agent, (x) => ({ ...x, steps: [...x.steps, String(d.step)] }));
      break;
    case 'agent_assessment': {
      const a = d as unknown as AgentAssessmentEvent;
      if (isAgent(a.agent))
        agentPatch(a.agent, (x) => ({ ...x, assessments: [...x.assessments, a] }));
      break;
    }
    case 'conflict_detected':
      next.conflicts = [
        ...v.conflicts,
        { ...(d as unknown as Conflict), event_id: v.events.at(-1)?.id },
      ];
      break;
    case 'coordinator_recommendation':
      next.coordinator = {
        ...next.coordinator,
        recs: [...v.coordinator.recs, d as unknown as CoordinatorEvent],
      };
      break;
    case 'human_review_required':
      next.reviews = [
        ...v.reviews,
        {
          review_id: String(d.review_id),
          event_id: String(d.event_id),
          summary: String(d.summary),
        },
      ];
      break;
    case 'review_recorded':
      next.reviews = v.reviews.map((r) =>
        r.review_id === d.review_id
          ? {
              ...r,
              decision: {
                decision: String(d.decision),
                reviewer_role: String(d.reviewer_role),
                comment: String(d.comment),
                audit_id: String(d.audit_id),
              },
            }
          : r,
      );
      break;
    case 'run_completed':
      next.completed = true;
      next.busy = false;
      break;
    case 'error':
      next.busy = false;
      next.error = String(d.message ?? 'Scenario error');
      break;
  }
  return next;
}
