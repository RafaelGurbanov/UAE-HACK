import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, ChevronRight, ClipboardCopy, Download, RefreshCw } from 'lucide-react';
import { useT, type MessageKey } from '../i18n';
import { api } from '../lib/api';
import { PIPELINE } from '../lib/labels';
import type { AgentId, AuditEntry, AuditQuery, PipelineNode } from '../lib/types';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorState, LoadingBlock } from '../components/ui/States';

const AGENTS: AgentId[] = [
  'legal_adviser',
  'data_protection',
  'education',
  'consumer_protection',
  'ai_ethics',
  'coordinator',
];
const RESULTS = [
  'answered',
  'no_source',
  'guidance',
  'general',
  'assessed',
  'consensus',
  'conflict',
  'approve',
  'override',
  'escalate',
];

export function AuditPage() {
  const t = useT();
  const [f, setF] = useState<AuditQuery>({ limit: 300 });
  const [msg, setMsg] = useState('');
  const q = useQuery({
    queryKey: ['audit', f],
    queryFn: () => api.audit(f),
    refetchInterval: 5000,
  });
  const set = (k: keyof AuditQuery, v: string) => setF((o) => ({ ...o, [k]: v || undefined }));

  const json = async () => JSON.stringify(q.data?.entries ?? [], null, 2);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(await json());
      setMsg(t('audit.copied'));
    } catch {
      setMsg(t('audit.copyFailed'));
    }
  };
  const download = async () => {
    const text = await api.exportAudit('json');
    const url = URL.createObjectURL(new Blob([text], { type: 'application/json' }));
    const a = Object.assign(document.createElement('a'), {
      href: url,
      download: `qalam-audit-${new Date().toISOString().slice(0, 19).replace(/:/g, '')}.json`,
    });
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    setMsg(t('audit.downloaded'));
  };

  const sel = 'rounded-lg border border-line bg-bg2 px-2 py-1.5 text-sm text-tx';
  return (
    <section>
      <PageHeader title={t('page.audit.title')} subtitle={t('page.audit.subtitle')} />
      <div className="card mb-4 flex flex-wrap items-end gap-3 p-4">
        <label className="flex flex-col gap-1 text-xs text-mut">
          {t('audit.agent')}
          <select
            className={sel}
            value={f.agent ?? ''}
            onChange={(e) => set('agent', e.target.value)}
          >
            <option value="">{t('audit.any')}</option>
            {AGENTS.map((a) => (
              <option key={a} value={a}>
                {t(`agent.${a}` as MessageKey)}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-mut">
          {t('audit.node')}
          <select
            className={sel}
            value={f.node ?? ''}
            onChange={(e) => set('node', e.target.value)}
          >
            <option value="">{t('audit.any')}</option>
            {PIPELINE.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-mut">
          {t('audit.result')}
          <select
            className={sel}
            value={f.outcome ?? ''}
            onChange={(e) => set('outcome', e.target.value)}
          >
            <option value="">{t('audit.any')}</option>
            {RESULTS.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </label>
        <div className="ms-auto flex flex-wrap gap-2">
          <button type="button" className="btn-ghost text-sm" onClick={() => void q.refetch()}>
            <RefreshCw size={14} aria-hidden /> {t('audit.refresh')}
          </button>
          <button type="button" className="btn-ghost text-sm" onClick={() => void copy()}>
            <ClipboardCopy size={14} aria-hidden /> {t('audit.copy')}
          </button>
          <button type="button" className="btn-primary text-sm" onClick={() => void download()}>
            <Download size={14} aria-hidden /> {t('audit.download')}
          </button>
        </div>
        <p role="status" className="w-full text-xs text-mut">
          {q.data ? t('audit.count', { n: q.data.entries.length, total: q.data.total }) : ''} {msg}
        </p>
      </div>
      {q.isLoading && <LoadingBlock lines={6} />}
      {q.isError && (
        <ErrorState message={(q.error as Error).message} onRetry={() => void q.refetch()} />
      )}
      {q.data && q.data.entries.length === 0 && <EmptyState title={t('audit.empty')} />}
      {q.data && q.data.entries.length > 0 && (
        <ol className="card divide-y divide-line overflow-hidden p-0 font-mono text-xs">
          {q.data.entries.map((e) => (
            <Row key={e.audit_id} e={e} />
          ))}
        </ol>
      )}
    </section>
  );
}

function Row({ e }: { e: AuditEntry }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  return (
    <li data-audit={e.audit_id}>
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="flex w-full flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 text-start hover:bg-card-strong"
      >
        {open ? (
          <ChevronDown size={13} aria-hidden />
        ) : (
          <ChevronRight size={13} aria-hidden className="rtl:rotate-180" />
        )}
        <span className="text-mut">{new Date(e.timestamp).toLocaleString()}</span>
        <span className="text-tx">{e.kind}</span>
        <span className="text-vio">{e.agent ?? '-'}</span>
        <span className="text-mut">{e.mode ?? '-'}</span>
        <span className="text-teal-ink">{e.outcome ?? '-'}</span>
        {e.matched_entry && (
          <span className="text-mut">
            {e.matched_entry}
            {e.score != null ? ` (${e.score})` : ''}
          </span>
        )}
        {e.requires_human_decision && <span className="text-amb-ink">{t('audit.human')}</span>}
        <span dir="auto" className="w-full truncate font-sans text-tx sm:w-auto sm:flex-1">
          {e.input_event}
        </span>
      </button>
      {open && (
        <div className="space-y-2 bg-bg2/60 px-3 py-3">
          <p>
            <span className="text-mut">audit_id:</span> {e.audit_id}{' '}
            {e.run_id && (
              <>
                <span className="text-mut"> run:</span> {e.run_id}
              </>
            )}
          </p>
          {e.reasoning_steps.length > 0 && (
            <div>
              <p className="text-mut">{t('audit.reasoning')}</p>
              <ol className="list-inside list-decimal">
                {e.reasoning_steps.map((s, i) => (
                  <li key={i} dir="auto">
                    {s}
                  </li>
                ))}
              </ol>
            </div>
          )}
          {e.retrieved_chunks.length > 0 && (
            <div>
              <p className="text-mut">{t('audit.retrieved')}</p>
              <ul>
                {e.retrieved_chunks.map((c) => (
                  <li key={c.chunk_id}>
                    {c.chunk_id} · {c.score}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {e.recommendation && (
            <p>
              <span className="text-mut">{t('audit.recommendation')}:</span>{' '}
              <span dir="auto">{e.recommendation}</span>
            </p>
          )}
          {e.pipeline_nodes.length > 0 && (
            <p>
              <span className="text-mut">nodes:</span>{' '}
              {(e.pipeline_nodes as PipelineNode[]).join(', ')}
            </p>
          )}
          <p className="text-mut">llm: {JSON.stringify(e.llm)}</p>
        </div>
      )}
    </li>
  );
}
