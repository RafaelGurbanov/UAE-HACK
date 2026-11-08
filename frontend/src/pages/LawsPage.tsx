import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useT } from '../i18n';
import { api } from '../lib/api';
import { legalKey } from '../lib/labels';
import type { KBLayer, LegalStatus } from '../lib/types';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorState, LoadingBlock } from '../components/ui/States';
import { LayerPill } from '../components/answer/Badges';
import { Command } from '../components/live/Command';

const th = 'px-3 py-2 text-start text-xs font-medium text-mut';
const td = 'px-3 py-2 align-top';

export function LawsPage() {
  const t = useT();
  const docs = useQuery({ queryKey: ['sources'], queryFn: () => api.sources() });
  const data = useQuery({ queryKey: ['data-entries'], queryFn: () => api.dataEntries() });
  return (
    <section>
      <PageHeader title={t('page.laws.title')} subtitle={t('page.laws.subtitle')} />

      <h2 className="mb-3 text-xl">{t('laws.documents')}</h2>
      {docs.isLoading && <LoadingBlock lines={4} />}
      {docs.isError && (
        <ErrorState message={(docs.error as Error).message} onRetry={() => void docs.refetch()} />
      )}
      {docs.data && docs.data.documents.length === 0 && (
        <EmptyState title={t('laws.noDocs')}>
          <p className="mb-2">{t('laws.noDocsHint')}</p>
          <Command cmd="powershell -ExecutionPolicy Bypass -File scripts\ingest.ps1" />
        </EmptyState>
      )}
      {docs.data && docs.data.documents.length > 0 && (
        <div className="card mb-10 overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-line">
              <tr>
                <th className={th}>{t('laws.title')}</th>
                <th className={th}>{t('drawer.layer')}</th>
                <th className={th}>{t('drawer.status')}</th>
                <th className={th}>{t('laws.lastChecked')}</th>
                <th className={th}>{t('laws.articles')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {docs.data.documents.map((d) => (
                <tr key={d.doc_id}>
                  <td className={td}>
                    <Link
                      to={`/laws/${encodeURIComponent(d.doc_id)}`}
                      className="text-tx underline decoration-gold/50 underline-offset-4 hover:decoration-gold"
                      dir="auto"
                    >
                      {d.title}
                    </Link>
                    {!d.verified && (
                      <span className="ms-2 text-xs text-amb-ink">{t('answer.toVerify')}</span>
                    )}
                  </td>
                  <td className={td}>
                    <LayerPill layer={d.layer} />
                  </td>
                  <td className={td}>{t(legalKey(d.status))}</td>
                  <td className={`${td} font-mono text-xs`}>
                    {d.retrieved_at?.slice(0, 10) ?? '-'}
                  </td>
                  <td className={`${td} font-mono text-xs`}>{d.chunk_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h2 className="mb-1 mt-8 text-xl">{t('laws.entries')}</h2>
      <p className="mb-3 text-sm text-mut">{t('laws.entriesHint')}</p>
      {data.isLoading && <LoadingBlock lines={4} />}
      {data.isError && (
        <ErrorState message={(data.error as Error).message} onRetry={() => void data.refetch()} />
      )}
      {data.data && data.data.entries.length === 0 && (
        <EmptyState title={t('laws.noEntries')}>
          <Command cmd="powershell -ExecutionPolicy Bypass -File scripts\validate-data.ps1" />
        </EmptyState>
      )}
      {data.data && data.data.errors.length > 0 && (
        <div role="alert" className="card mb-3 border-red/40 p-3 text-sm text-red-ink">
          {data.data.errors.join(' · ')}
        </div>
      )}
      {data.data && data.data.entries.length > 0 && (
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-line">
              <tr>
                <th className={th}>{t('laws.question')}</th>
                <th className={th}>{t('drawer.layer')}</th>
                <th className={th}>{t('drawer.status')}</th>
                <th className={th}>{t('laws.lastChecked')}</th>
                <th className={th}>{t('laws.verified')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {data.data.entries.map((e) => (
                <tr key={e.id}>
                  <td className={td}>
                    <Link
                      to={`/laws/entry/${encodeURIComponent(e.id)}`}
                      className="text-tx underline decoration-gold/50 underline-offset-4 hover:decoration-gold"
                      dir="auto"
                    >
                      {e.question}
                    </Link>
                    <div className="font-mono text-[11px] text-mut">
                      {e.id} · {e.topic}
                    </div>
                  </td>
                  <td className={td}>
                    <div className="flex flex-wrap gap-1">
                      {e.layers.map((l: KBLayer) => (
                        <LayerPill key={l} layer={l} />
                      ))}
                    </div>
                  </td>
                  <td className={td}>{statusLabel(t, e.status)}</td>
                  <td className={`${td} font-mono text-xs`}>{e.last_checked ?? '-'}</td>
                  <td className={`${td} text-xs`}>
                    {e.verified_citations === e.citations && e.citations > 0 ? (
                      <span className="text-teal-ink">{t('answer.verified')}</span>
                    ) : (
                      <span className="text-amb-ink">
                        {t('laws.verifiedCount', { v: e.verified_citations, c: e.citations })}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function statusLabel(t: ReturnType<typeof useT>, s: string) {
  const known: LegalStatus[] = ['in_force', 'amended', 'repealed', 'not_legislation', 'unknown'];
  if ((known as string[]).includes(s)) return t(legalKey(s as LegalStatus));
  if (s === 'placeholder') return t('laws.placeholder');
  return s;
}
