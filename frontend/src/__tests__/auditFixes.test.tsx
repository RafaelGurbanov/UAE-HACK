import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { api } from '../lib/api';
import { emptyView, maxSeverity, reduce } from '../lib/scenarioState';
import type { AskResponse, AuditEntry, PolicyGap, StreamEnvelope } from '../lib/types';
import { SearchHero } from '../components/search/SearchHero';
import { GuidanceView } from '../components/answer/AnswerView';
import { GapsPage } from '../pages/GapsPage';
import { AuditPage } from '../pages/AuditPage';
import { LawsPage } from '../pages/LawsPage';
import { useUi } from '../stores/ui';

const wrap = (ui: ReactNode) =>
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );

beforeEach(() => act(() => useUi.getState().setLang('en')));
afterEach(() => vi.restoreAllMocks());

// ---------------- scenario reducer ----------------
let seq = 0;
const env = (type: StreamEnvelope['type'], data: Record<string, unknown>): StreamEnvelope => ({
  type,
  run_id: 'r',
  seq: ++seq,
  ts: '',
  data,
});

test('scenario reducer: information asymmetry, severity shift, dedupe and reset', () => {
  seq = 0;
  let v = reduce(emptyView(), { type: 'release' });
  expect(v.busy).toBe(true);
  const e1 = env('event_released', {
    id: 'e1',
    step: 1,
    at: '',
    title: 'One',
    description: '',
    severity: 'info',
    visible_to: ['education'],
    pipeline_nodes: ['SRC'],
  });
  v = reduce(v, { type: 'envelope', env: e1 });
  v = reduce(v, { type: 'envelope', env: e1 }); // replay is ignored
  expect(v.events).toHaveLength(1);
  expect(v.agents.education.seen).toEqual(['e1']);
  expect(v.agents.data_protection.seen).toEqual([]);
  v = reduce(v, {
    type: 'envelope',
    env: env('event_released', {
      id: 'e2',
      step: 2,
      at: '',
      title: 'Two',
      description: '',
      severity: 'critical',
      visible_to: ['data_protection'],
      pipeline_nodes: [],
    }),
  });
  expect(maxSeverity(v)).toBe('critical');
  v = reduce(v, {
    type: 'envelope',
    env: env('agent_status', { agent: 'coordinator', state: 'done' }),
  });
  expect(v.busy).toBe(false);
  expect(reduce(v, { type: 'reset' }).events).toHaveLength(0);
});

// ---------------- search ----------------
test('very short input shows a gentle prompt and does not call the API', async () => {
  const onAsk = vi.fn();
  wrap(<SearchHero busy={false} onAsk={onAsk} />);
  const ask = screen.getByRole('button', { name: /^Ask/ });
  expect(ask).toBeEnabled();
  await userEvent.click(ask);
  expect(screen.getByText(/at least 3 characters/)).toBeInTheDocument();
  await userEvent.type(screen.getByRole('textbox'), 'hi{Enter}');
  expect(onAsk).not.toHaveBeenCalled();
  await userEvent.type(screen.getByRole('textbox'), 'gh{Enter}');
  expect(onAsk).toHaveBeenCalledWith('high');
  expect(screen.queryByText(/at least 3 characters/)).not.toBeInTheDocument();
});

test('greeting guidance renders clickable example questions', async () => {
  const onExample = vi.fn();
  const res = {
    outcome: 'guidance',
    mode: 'guidance',
    answer: { short_answer: 'Hello! Ask a question about children’s data.' },
    suggested_topics: ['Can an app show targeted ads to minors?'],
  } as unknown as AskResponse;
  wrap(<GuidanceView result={res} onExample={onExample} />);
  await userEvent.click(
    screen.getByRole('button', { name: 'Can an app show targeted ads to minors?' }),
  );
  expect(onExample).toHaveBeenCalledWith('Can an app show targeted ads to minors?');
});

// ---------------- gaps ----------------
const gap = (id: string, gap_type: PolicyGap['gap_type']): PolicyGap =>
  ({
    id,
    title: `Gap ${id}`,
    gap_type,
    domain: 'education',
    uae_says: {
      statement: 'UAE statement',
      citations: [
        {
          law: 'SOURCE TO BE VERIFIED',
          article: 'SOURCE TO BE VERIFIED',
          layer: 'uae_federal',
          url: '',
          quote: 'SOURCE TO BE VERIFIED',
          verified: false,
        },
      ],
    },
    global_example_says: { statement: 'Global statement', citations: [] },
    gap_analysis: 'ANALYSIS (not law): x',
    recommendation: 'Do y',
    severity: 'high',
    pipeline_nodes: ['D'],
    readiness_dimensions: ['ai_policy_implementation'],
  }) as unknown as PolicyGap;

test('gap board: three columns, source-to-verify label and type filter', async () => {
  const spy = vi.spyOn(api, 'gaps').mockImplementation(async (q = {}) => {
    const all = [gap('a', 'legislative_gap'), gap('b', 'missing_standard')];
    return {
      gaps: all.filter((g) => !q.gap_type || g.gap_type === q.gap_type),
      readiness_radar: { ai_policy_implementation: 1 },
    };
  });
  wrap(<GapsPage />);
  expect(await screen.findByText('Gap a')).toBeInTheDocument();
  expect(screen.getAllByText('UAE says').length).toBe(2);
  expect(screen.getAllByText('Global example says').length).toBe(2);
  expect(screen.getAllByText('Gap (analysis, not law)').length).toBe(2);
  expect(screen.getAllByText('Source to be verified').length).toBeGreaterThan(0);
  expect(screen.getByTestId('radar')).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Legislative gap' }));
  await waitFor(() => expect(screen.queryByText('Gap b')).not.toBeInTheDocument());
  expect(spy).toHaveBeenLastCalledWith({ gap_type: 'legislative_gap' });
});

// ---------------- audit ----------------
const entry: AuditEntry = {
  audit_id: 'aud_1',
  timestamp: new Date().toISOString(),
  kind: 'ask',
  mode: 'offline_json',
  outcome: 'answered',
  matched_entry: 'children-data-consent',
  score: 0.9,
  agent: 'legal_adviser',
  run_id: null,
  input_event: 'consent question',
  retrieved_chunks: [],
  reasoning_steps: ['matched entry'],
  recommendation: null,
  citations: [],
  confidence: null,
  pipeline_nodes: ['SRC'],
  readiness_dimensions: [],
  requires_human_decision: true,
  llm: { calls: 0 },
} as AuditEntry;

test('audit trail: rows expand, filters query the API, download produces valid JSON', async () => {
  const audit = vi.spyOn(api, 'audit').mockResolvedValue({ entries: [entry], total: 1 });
  const exp = vi.spyOn(api, 'exportAudit').mockResolvedValue(JSON.stringify([entry]));
  let blob: Blob | null = null;
  URL.createObjectURL = vi.fn((b: Blob) => {
    blob = b;
    return 'blob:x';
  }) as typeof URL.createObjectURL;
  URL.revokeObjectURL = vi.fn();
  const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  wrap(<AuditPage />);
  const row = await screen.findByRole('button', { name: /consent question/ });
  expect(within(row).getByText('human review')).toBeInTheDocument();
  await userEvent.click(row);
  expect(row).toHaveAttribute('aria-expanded', 'true');
  expect(screen.getByText('matched entry')).toBeInTheDocument();
  await userEvent.selectOptions(screen.getByLabelText('Result'), 'answered');
  await waitFor(() =>
    expect(audit).toHaveBeenLastCalledWith(expect.objectContaining({ outcome: 'answered' })),
  );
  await userEvent.click(screen.getByRole('button', { name: /Download JSON/ }));
  expect(exp).toHaveBeenCalledWith('json');
  expect(click).toHaveBeenCalled();
  const text = await new Promise<string>((ok) => {
    const r = new FileReader();
    r.onload = () => ok(String(r.result));
    r.readAsText(blob as unknown as Blob);
  });
  expect(JSON.parse(text)[0].audit_id).toBe('aud_1');
});

// ---------------- laws ----------------
test('laws page: empty documents state shows the ingest command; entries link to detail', async () => {
  vi.spyOn(api, 'sources').mockResolvedValue({
    documents: [],
    coverage: [],
    total_documents: 0,
    total_chunks: 0,
  });
  vi.spyOn(api, 'dataEntries').mockResolvedValue({
    entries: [
      {
        id: 'children-data-consent',
        topic: 'consent',
        question: 'What consent is needed?',
        status: 'placeholder',
        last_checked: null,
        layers: ['uae_federal'],
        citations: 1,
        verified_citations: 0,
        file: 'x.json',
      },
    ],
    errors: [],
  });
  wrap(<LawsPage />);
  expect(await screen.findByText('No documents ingested yet')).toBeInTheDocument();
  expect(screen.getByText(/scripts\\ingest\.ps1/)).toBeInTheDocument();
  const link = await screen.findByRole('link', { name: 'What consent is needed?' });
  expect(link).toHaveAttribute('href', '/laws/entry/children-data-consent');
  expect(screen.getByText('0 of 1 verified')).toBeInTheDocument();
});
