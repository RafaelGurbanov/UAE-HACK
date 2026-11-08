import { CircleCheck, Database, TriangleAlert } from 'lucide-react';
import { useT } from '../../i18n';
import { useHealth } from '../../hooks/useHealth';
import { MOCK } from '../../lib/env';
import { LiveProblem } from './LiveProblem';

/** One-line live status, or an actionable problem card when the backend is not ready. */
export function BackendStatus() {
  const t = useT();
  const h = useHealth();
  if (MOCK) return null;
  if (h.isLoading) return <p className="h-5 text-xs text-mut" aria-hidden />;
  if (h.isError) return <LiveProblem kind="network" onRetry={() => void h.refetch()} />;
  const d = h.data!;
  if (d.answer_mode === 'offline' && d.status === 'ok')
    return (
      <p role="status" className="flex items-center justify-center gap-1.5 text-xs text-mut">
        <Database size={13} className="text-teal" aria-hidden />
        {t('offline.status', { n: d.data_entries ?? 0 })}
      </p>
    );
  if (d.answer_mode !== 'offline' && !d.llm_configured)
    return <LiveProblem kind="llm_unavailable" onRetry={() => void h.refetch()} />;
  if (d.answer_mode !== 'offline' && d.kb_chunks === 0)
    return <LiveProblem kind="kb_empty" onRetry={() => void h.refetch()} />;
  if (d.status === 'degraded')
    return (
      <div role="status" className="card flex items-start gap-2 border-amb/40 p-3 text-sm">
        <TriangleAlert size={16} className="mt-0.5 shrink-0 text-amb" aria-hidden />
        <div>
          <p className="font-medium text-tx">{t('live.degraded')}</p>
          <ul className="list-inside list-disc text-mut">
            {d.problems.map((p) => (
              <li key={p} dir="auto">
                {p}
              </li>
            ))}
          </ul>
        </div>
      </div>
    );
  return (
    <p role="status" className="flex items-center justify-center gap-1.5 text-xs text-mut">
      <CircleCheck size={13} className="text-teal" aria-hidden />
      {t('live.status', { model: d.llm_model, chunks: d.index_chunks })}
    </p>
  );
}
