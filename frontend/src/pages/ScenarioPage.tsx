import { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  CheckCircle2,
  Loader2,
  Play,
  RotateCcw,
  ShieldAlert,
  SkipForward,
  TriangleAlert,
} from 'lucide-react';
import { useT, type MessageKey } from '../i18n';
import { api } from '../lib/api';
import {
  emptyView,
  maxSeverity,
  reduce,
  SCENARIO_AGENTS,
  type AgentView,
  type ReviewView,
} from '../lib/scenarioState';
import type { ReviewDecision, ScenarioAgent } from '../lib/types';
import { PageHeader } from '../components/ui/PageHeader';
import { ErrorState, LoadingBlock } from '../components/ui/States';
import { CitationList, ConfidenceRing, SeverityPill } from '../components/ui/Bits';
import { PipelineMap } from '../components/pipeline/PipelineMap';
import { RequiresDecision } from '../components/answer/Badges';

const SEV_BAR = { info: 'bg-blu', warning: 'bg-amb', critical: 'bg-red' } as const;

export function ScenarioPage() {
  const t = useT();
  const list = useQuery({ queryKey: ['scenarios'], queryFn: () => api.scenarios() });
  const [scenarioId, setScenarioId] = useState<string>('');
  const [runId, setRunId] = useState<string | null>(null);
  const [view, dispatch] = useReducer(reduce, undefined, emptyView);
  const unsub = useRef<null | (() => void)>(null);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    if (!scenarioId && list.data?.length)
      setScenarioId((list.data.find((s) => !s.controversial) ?? list.data[0]!).id);
  }, [list.data, scenarioId]);
  useEffect(() => () => unsub.current?.(), []);

  const scenario = list.data?.find((s) => s.id === scenarioId);
  const total = scenario?.total_events ?? 0;

  const start = useCallback(async (id: string) => {
    unsub.current?.();
    setRunId(null);
    dispatch({ type: 'reset' });
    setStarting(true);
    try {
      const r = await api.startScenario(id);
      unsub.current = api.subscribeScenario(id, r.run_id, (env) =>
        dispatch({ type: 'envelope', env }),
      );
      setRunId(r.run_id);
    } catch (e) {
      dispatch({ type: 'fail', message: e instanceof Error ? e.message : String(e) });
    } finally {
      setStarting(false);
    }
  }, []);

  const release = async () => {
    if (!runId) return;
    dispatch({ type: 'release' });
    try {
      await api.nextEvent(scenarioId, runId);
    } catch (e) {
      dispatch({ type: 'fail', message: e instanceof Error ? e.message : String(e) });
    }
  };

  const done = view.events.length >= total && total > 0;
  const sev = maxSeverity(view);

  return (
    <section>
      <PageHeader title={t('page.scenario.title')} subtitle={t('page.scenario.subtitle')} />

      <div className="card mb-6 flex flex-wrap items-end gap-3 p-4">
        <label className="flex min-w-0 flex-1 flex-col gap-1 text-sm">
          <span className="text-mut">{t('scenario.pick')}</span>
          <select
            value={scenarioId}
            onChange={(e) => {
              setScenarioId(e.target.value);
              unsub.current?.();
              setRunId(null);
              dispatch({ type: 'reset' });
            }}
            className="rounded-xl border border-line bg-bg2 px-3 py-2 text-tx"
          >
            {list.data?.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title}
                {s.controversial ? ` (${t('scenario.controversial')})` : ''}
              </option>
            ))}
          </select>
        </label>
        {!runId ? (
          <button
            type="button"
            className="btn-primary"
            disabled={!scenarioId || starting}
            onClick={() => void start(scenarioId)}
          >
            <Play size={16} aria-hidden /> {t('scenario.start')}
          </button>
        ) : (
          <>
            <button
              type="button"
              className="btn-primary"
              disabled={view.busy || done}
              data-testid="release-next"
              onClick={() => void release()}
            >
              {view.busy ? (
                <Loader2 size={16} className="animate-spin" aria-hidden />
              ) : (
                <SkipForward size={16} aria-hidden />
              )}
              {done ? t('scenario.allReleased') : t('scenario.next')}
            </button>
            <button type="button" className="btn-ghost" onClick={() => void start(scenarioId)}>
              <RotateCcw size={15} aria-hidden /> {t('scenario.restart')}
            </button>
          </>
        )}
        <p className="w-full text-xs text-mut" aria-live="polite">
          {runId ? t('scenario.progress', { n: view.events.length, total }) : scenario?.description}
          {' · '}
          {t('scenario.offlineNote')}
        </p>
      </div>

      {list.isLoading && <LoadingBlock lines={3} />}
      {list.isError && (
        <ErrorState message={(list.error as Error).message} onRetry={() => void list.refetch()} />
      )}
      {view.error && <ErrorState message={view.error} />}

      {runId && (
        <div className="space-y-6">
          <div
            role="status"
            className={`flex items-center gap-3 rounded-xl px-4 py-2 text-sm font-medium text-white ${sev ? SEV_BAR[sev] : 'bg-blu'}`}
            data-severity={sev ?? 'info'}
          >
            <span>{t(`scenario.level.${sev ?? 'info'}` as MessageKey)}</span>
          </div>

          <Timeline events={view.events} total={total} />

          <PipelineMap active={view.highlight.nodes} pulseKey={view.lastSeq} />

          <div>
            <h2 className="mb-3 text-xl">{t('scenario.council')}</h2>
            <div className="grid gap-4 md:grid-cols-2">
              {SCENARIO_AGENTS.map((a) => (
                <AgentCard key={a} agent={a} v={view.agents[a]} events={view.events} />
              ))}
            </div>
          </div>

          <CoordinatorPanel view={view} />

          {view.reviews.length > 0 && <HumanReview reviews={view.reviews} />}
        </div>
      )}
    </section>
  );
}

function Timeline({
  events,
  total,
}: {
  events: ReturnType<typeof emptyView>['events'];
  total: number;
}) {
  const t = useT();
  const dot = { info: 'bg-blu', warning: 'bg-amb', critical: 'bg-red' } as const;
  return (
    <div className="card p-4 sm:p-5">
      <h2 className="mb-3 text-lg">{t('scenario.timeline')}</h2>
      {events.length === 0 && <p className="text-sm text-mut">{t('scenario.noEvents')}</p>}
      <ol className="space-y-3">
        {events.map((e) => (
          <li key={e.id} className="flex gap-3" data-testid="timeline-event">
            <span
              className={`mt-1.5 size-3 shrink-0 rounded-full ${dot[e.severity]}`}
              aria-hidden
            />
            <div className="min-w-0">
              <p className="flex flex-wrap items-center gap-2 text-sm font-semibold text-tx">
                {e.step}. {e.title} <SeverityPill level={e.severity} />{' '}
                <span className="text-xs font-normal text-mut">{e.at}</span>
              </p>
              <p className="text-sm text-mut">{e.description}</p>
              <p className="text-xs text-mut">
                {t('scenario.visibleTo')}:{' '}
                {e.visible_to.map((a) => t(`agent.${a}` as MessageKey)).join(', ')}
              </p>
            </div>
          </li>
        ))}
        {Array.from({ length: Math.max(0, total - events.length) }, (_, i) => (
          <li key={`f${i}`} className="flex gap-3 opacity-50" aria-hidden>
            <span className="mt-1.5 size-3 shrink-0 rounded-full border border-line" />
            <span className="text-sm text-mut">{t('scenario.pending')}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

const STATUS_STYLE = {
  idle: 'text-mut border-line',
  thinking: 'text-amb-ink border-amb/50',
  done: 'text-teal-ink border-teal/50',
};

function AgentCard({
  agent,
  v,
  events,
}: {
  agent: ScenarioAgent;
  v: AgentView;
  events: { id: string; title: string }[];
}) {
  const t = useT();
  const last = v.assessments.at(-1);
  const seen = events.filter((e) => v.seen.includes(e.id));
  return (
    <article
      className="card space-y-3 p-4"
      aria-labelledby={`agent-${agent}`}
      data-agent={agent}
      data-status={v.status}
    >
      <header className="flex items-center gap-2">
        <h3 id={`agent-${agent}`} className="text-base">
          {t(`agent.${agent}` as MessageKey)}
        </h3>
        <span
          className={`pill ms-auto border px-2 py-0.5 text-[11px] ${STATUS_STYLE[v.status]}`}
          data-status={v.status}
        >
          {v.status === 'thinking' && (
            <Loader2 size={11} className="me-1 inline animate-spin" aria-hidden />
          )}
          {t(`status.agent.${v.status}` as MessageKey)}
        </span>
      </header>
      <div>
        <p className="text-xs font-semibold text-mut">{t('scenario.seen')}</p>
        {seen.length ? (
          <ul className="list-inside list-disc text-xs text-tx">
            {seen.map((e) => (
              <li key={e.id}>{e.title}</li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-mut">{t('scenario.notInformed')}</p>
        )}
      </div>
      {last && (
        <div className="space-y-2 border-t border-line pt-3">
          <div className="flex items-start gap-3">
            <ConfidenceRing value={last.confidence} />
            <div className="min-w-0 space-y-1">
              <p className={`text-sm ${last.no_source ? 'text-amb-ink' : 'text-mut'}`}>
                {last.summary}
              </p>
              <p className="text-sm text-tx">{last.recommendation}</p>
              <p className="text-xs text-mut">
                {t('scenario.stance')}: <span className="font-mono">{last.stance}</span>
              </p>
            </div>
          </div>
          <CitationList items={last.citations} />
          {last.requires_human_decision && <RequiresDecision />}
        </div>
      )}
    </article>
  );
}

function CoordinatorPanel({ view }: { view: ReturnType<typeof emptyView> }) {
  const t = useT();
  const rec = view.coordinator.recs.at(-1);
  const conflicts = rec ? rec.conflicts : [];
  return (
    <section className="card space-y-3 p-4 sm:p-5" aria-labelledby="coord-title">
      <header className="flex items-center gap-2">
        <h2 id="coord-title" className="text-lg">
          {t('agent.coordinator')}
        </h2>
        <span
          className={`pill ms-auto border px-2 py-0.5 text-[11px] ${STATUS_STYLE[view.coordinator.status]}`}
        >
          {t(`status.agent.${view.coordinator.status}` as MessageKey)}
        </span>
      </header>
      {!rec && <p className="text-sm text-mut">{t('scenario.coordWaiting')}</p>}
      {rec && (
        <>
          {conflicts.length > 0 ? (
            <ul className="space-y-2">
              {conflicts.map((c, i) => (
                <li
                  key={i}
                  role="alert"
                  className="flex items-start gap-2 rounded-xl border border-red/50 bg-red/10 px-3 py-2 text-sm text-red-ink"
                >
                  <TriangleAlert size={16} className="mt-0.5 shrink-0" aria-hidden />
                  <span>
                    <b>{t('scenario.conflict')}:</b> {c.description}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="flex items-center gap-2 text-sm text-teal-ink">
              <CheckCircle2 size={15} aria-hidden /> {t('scenario.noConflict')}
            </p>
          )}
          <p className="text-tx">{rec.recommendation}</p>
          {rec.actions.length > 0 && (
            <ul className="list-inside list-decimal space-y-1 text-sm text-tx">
              {rec.actions.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
          )}
          {rec.expected_handling.length > 0 && (
            <div className="rounded-xl border border-teal/40 bg-teal/5 p-3">
              <p className="mb-1 text-xs font-semibold text-teal-ink">{t('scenario.expected')}</p>
              <ul className="list-inside list-disc text-sm text-tx">
                {rec.expected_handling.map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            </div>
          )}
          {rec.requires_human_decision && <RequiresDecision />}
        </>
      )}
    </section>
  );
}

function HumanReview({ reviews }: { reviews: ReviewView[] }) {
  const t = useT();
  return (
    <section className="card space-y-4 border-amb/40 p-4 sm:p-5" aria-labelledby="hitl-title">
      <h2 id="hitl-title" className="flex items-center gap-2 text-lg">
        <ShieldAlert size={18} className="text-amb" aria-hidden /> {t('hitl.title')}
      </h2>
      {reviews.map((r) => (
        <ReviewItem key={r.review_id} r={r} />
      ))}
    </section>
  );
}

function ReviewItem({ r }: { r: ReviewView }) {
  const t = useT();
  const [comment, setComment] = useState('');
  const [role, setRole] = useState<ReviewDecision['reviewer_role']>('regulator');
  const [sending, setSending] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [local, setLocal] = useState<{ decision: string; audit_id: string } | null>(null);
  const decided = r.decision ?? local;
  const send = async (decision: ReviewDecision['decision']) => {
    // approve may be recorded without a comment; override and escalate need a reason
    if (decision !== 'approve' && comment.trim().length < 3) {
      setErr(t('hitl.needComment'));
      return;
    }
    setSending(true);
    setErr(null);
    try {
      const res = await api.reviewDecision(r.review_id, {
        decision,
        reviewer_role: role,
        comment: comment.trim().length >= 3 ? comment.trim() : 'Approved without comment',
      });
      setLocal({ decision: res.decision, audit_id: res.audit_id });
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setSending(false);
    }
  };
  return (
    <div className="space-y-2 border-t border-line pt-3" data-review={r.review_id}>
      <p className="text-sm text-tx">{r.summary}</p>
      {decided ? (
        <p role="status" className="flex items-center gap-2 text-sm text-teal-ink">
          <CheckCircle2 size={15} aria-hidden />{' '}
          {t('hitl.recorded', {
            d: t(`hitl.${decided.decision}` as MessageKey),
            id: decided.audit_id,
          })}
        </p>
      ) : (
        <>
          <div className="flex flex-wrap gap-2">
            <label className="flex flex-col gap-1 text-xs text-mut">
              {t('hitl.role')}
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as typeof role)}
                className="rounded-lg border border-line bg-bg2 px-2 py-1.5 text-sm text-tx"
              >
                <option value="regulator">{t('hitl.regulator')}</option>
                <option value="counsellor">{t('hitl.counsellor')}</option>
                <option value="school_admin">{t('hitl.school_admin')}</option>
              </select>
            </label>
            <label className="flex min-w-0 flex-1 flex-col gap-1 text-xs text-mut">
              {t('hitl.comment')}
              <input
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                className="rounded-lg border border-line bg-bg2 px-2 py-1.5 text-sm text-tx"
              />
            </label>
          </div>
          <div className="flex flex-wrap gap-2">
            {(['approve', 'override', 'escalate'] as const).map((d) => (
              <button
                key={d}
                type="button"
                disabled={sending}
                onClick={() => void send(d)}
                className={d === 'approve' ? 'btn-primary text-sm' : 'btn-ghost text-sm'}
              >
                {t(`hitl.${d}` as MessageKey)}
              </button>
            ))}
          </div>
          {err && (
            <p role="alert" className="text-xs text-red-ink">
              {err}
            </p>
          )}
        </>
      )}
    </div>
  );
}
