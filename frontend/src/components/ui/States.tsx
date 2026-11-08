import { AlertTriangle, Inbox } from 'lucide-react';
import type { ReactNode } from 'react';
import { useT } from '../../i18n';

export function Skeleton({ className = '' }: { className?: string }) {
  return <div aria-hidden className={`skeleton ${className}`} />;
}

export function LoadingBlock({ lines = 3 }: { lines?: number }) {
  const t = useT();
  return (
    <div role="status" aria-live="polite" className="space-y-3">
      <span className="sr-only">{t('common.loading')}</span>
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton key={i} className={`h-4 ${i === lines - 1 ? 'w-2/3' : 'w-full'}`} />
      ))}
    </div>
  );
}

export function EmptyState({ title, children }: { title?: string; children?: ReactNode }) {
  const t = useT();
  return (
    <div className="card flex flex-col items-center gap-2 p-10 text-center">
      <Inbox className="text-mut" aria-hidden />
      <p className="text-tx">{title ?? t('common.empty')}</p>
      {children && <div className="w-full min-w-0 text-sm text-mut">{children}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message?: string; onRetry?: () => void }) {
  const t = useT();
  return (
    <div
      role="alert"
      className="card flex flex-col items-center gap-3 border-red/40 p-8 text-center"
    >
      <AlertTriangle className="text-red-ink" aria-hidden />
      <p className="text-tx">{t('common.error')}</p>
      {message && <p className="text-sm text-mut">{message}</p>}
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-full border border-line px-4 py-1.5 text-sm hover:border-line-strong"
        >
          {t('common.retry')}
        </button>
      )}
    </div>
  );
}
