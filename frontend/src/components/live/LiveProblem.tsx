import { DatabaseZap, KeyRound, PlugZap, RefreshCw } from 'lucide-react';
import type { ReactNode } from 'react';
import { useT } from '../../i18n';
import { API_LABEL } from '../../lib/env';
import { Command } from './Command';

export type ProblemKind = 'network' | 'llm_unavailable' | 'kb_empty';

export const START_BACKEND = '.\\scripts\\start-backend.ps1';
export const START_BACKEND_MANUAL =
  'cd backend; .\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --reload --port 8000';
export const INGEST = '.\\scripts\\ingest.ps1';

function Frame({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <article role="alert" className="card space-y-3 border-amb/40 p-5 sm:p-6">
      <h2 className="flex items-center gap-2 text-lg">
        {icon} {title}
      </h2>
      {children}
    </article>
  );
}

/** Clear, actionable states for a live backend that cannot answer yet. */
export function LiveProblem({
  kind,
  message,
  onRetry,
}: {
  kind: ProblemKind;
  message?: string;
  onRetry?: () => void;
}) {
  const t = useT();
  const retry = onRetry && (
    <button type="button" onClick={onRetry} className="btn-ghost text-sm">
      <RefreshCw size={14} aria-hidden /> {t('live.retry')}
    </button>
  );
  if (kind === 'network')
    return (
      <Frame icon={<PlugZap className="text-amb" aria-hidden />} title={t('live.downTitle')}>
        <p className="text-mut">{t('live.downBody', { url: API_LABEL })}</p>
        <Command cmd={START_BACKEND} />
        <p className="text-xs text-mut">{t('live.downAlt')}</p>
        <Command cmd={START_BACKEND_MANUAL} />
        {retry}
      </Frame>
    );
  if (kind === 'llm_unavailable')
    return (
      <Frame icon={<KeyRound className="text-amb" aria-hidden />} title={t('live.llmTitle')}>
        <p className="text-mut">{t('live.llmBody')}</p>
        <Command cmd={'ANTHROPIC_API_KEY=sk-ant-...   (in .env)'} />
        <Command cmd={START_BACKEND} />
        {message && (
          <p className="text-xs text-mut" dir="auto">
            {message}
          </p>
        )}
        {retry}
      </Frame>
    );
  return (
    <Frame icon={<DatabaseZap className="text-amb" aria-hidden />} title={t('live.kbTitle')}>
      <p className="text-mut">{t('live.kbBody')}</p>
      <Command cmd={INGEST} />
      {retry}
    </Frame>
  );
}
