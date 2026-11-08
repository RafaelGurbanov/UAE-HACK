import { useEffect } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, ExternalLink } from 'lucide-react';
import { useT } from '../i18n';
import { api } from '../lib/api';
import { useLaw } from '../hooks/useLaw';
import { legalKey } from '../lib/labels';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorState, LoadingBlock } from '../components/ui/States';
import {
  DimensionBadges,
  LayerPill,
  NodeBadges,
  RequiresDecision,
} from '../components/answer/Badges';
import { CitationList } from '../components/ui/Bits';
import { statusLabel } from './LawsPage';

const anchor = (a: string) => `art-${a.replace(/[^\w؀-ۿ-]+/g, '-')}`;

function Back() {
  const t = useT();
  return (
    <Link to="/laws" className="mb-4 inline-flex items-center gap-1 text-sm text-mut hover:text-tx">
      <ArrowLeft size={14} aria-hidden className="rtl:rotate-180" /> {t('laws.back')}
    </Link>
  );
}

export function LawDetailPage() {
  const t = useT();
  const { id } = useParams();
  const { hash } = useLocation();
  const q = useLaw(id);
  useEffect(() => {
    if (q.data && hash)
      document.getElementById(decodeURIComponent(hash.slice(1)))?.scrollIntoView();
  }, [q.data, hash]);
  if (q.isLoading)
    return (
      <section>
        <Back />
        <LoadingBlock lines={8} />
      </section>
    );
  if (q.isError)
    return (
      <section>
        <Back />
        <ErrorState message={(q.error as Error).message} onRetry={() => void q.refetch()} />
      </section>
    );
  if (!q.data) return null;
  const { document: d, articles } = q.data;
  return (
    <section>
      <Back />
      <PageHeader
        title={d.title}
        subtitle={[d.issuing_body, d.law_number, d.year].filter(Boolean).join(' · ')}
      />
      <div className="mb-6 flex flex-wrap items-center gap-2 text-sm">
        <LayerPill layer={d.layer} />
        <span className="pill border border-line px-2 py-0.5 text-xs">{t(legalKey(d.status))}</span>
        {!d.verified && <span className="text-xs text-amb-ink">{t('answer.toVerify')}</span>}
        {d.url ? (
          <a
            href={d.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-xs text-teal-ink underline"
          >
            {t('drawer.official')} <ExternalLink size={12} aria-hidden />
          </a>
        ) : (
          <span className="text-xs text-mut">{t('drawer.noLink')}</span>
        )}
      </div>
      {articles.length === 0 ? (
        <EmptyState title={t('laws.noArticles')} />
      ) : (
        <div className="grid gap-6 md:grid-cols-[200px_1fr]">
          <nav
            aria-label={t('laws.articleNav')}
            className="card h-fit max-h-[70vh] overflow-y-auto p-3 md:sticky md:top-20"
          >
            <ol className="space-y-1 text-sm">
              {articles.map((a) => (
                <li key={a.article}>
                  <a
                    href={`#${anchor(a.article)}`}
                    className="block rounded px-2 py-1 text-mut hover:bg-card-strong hover:text-tx"
                  >
                    {t('answer.article', { a: a.article })}
                    {a.heading ? ` · ${a.heading}` : ''}
                  </a>
                </li>
              ))}
            </ol>
          </nav>
          <div className="space-y-4">
            {articles.map((a) => (
              <article key={a.article} id={anchor(a.article)} className="card scroll-mt-24 p-4">
                <h2 className="mb-2 text-lg">
                  {t('answer.article', { a: a.article })}
                  {a.heading ? ` · ${a.heading}` : ''}
                </h2>
                {a.amended && <p className="mb-1 text-xs text-amb-ink">{t('legal.amended')}</p>}
                <p dir="auto" className="whitespace-pre-line text-sm leading-relaxed text-tx">
                  {a.text}
                </p>
              </article>
            ))}
          </div>
        </div>
      )}
      <p className="mt-6 text-xs text-mut">{t('drawer.authoritative')}</p>
    </section>
  );
}

export function EntryDetailPage() {
  const t = useT();
  const { id } = useParams();
  const q = useQuery({
    queryKey: ['data-entry', id],
    queryFn: () => api.dataEntry(id!),
    enabled: !!id,
    retry: false,
  });
  if (q.isLoading)
    return (
      <section>
        <Back />
        <LoadingBlock lines={6} />
      </section>
    );
  if (q.isError)
    return (
      <section>
        <Back />
        <ErrorState message={(q.error as Error).message} onRetry={() => void q.refetch()} />
      </section>
    );
  if (!q.data) return null;
  const e = q.data;
  return (
    <section>
      <Back />
      <PageHeader title={e.question} subtitle={`${e.topic} · ${e.id}`} />
      <div className="mb-4 flex flex-wrap gap-3 text-xs text-mut">
        <span>
          {t('drawer.status')}: {statusLabel(t, e.status)}
        </span>
        <span>
          {t('laws.lastChecked')}: {e.last_checked ?? '-'}
        </span>
        <span className="font-mono">{e.file}</span>
      </div>
      <p className="mb-2 text-xs font-medium text-teal-ink">{t('offline.label')}</p>
      <div className="card mb-6 p-4">
        <p dir="auto" className="whitespace-pre-line text-tx">
          {e.answer}
        </p>
      </div>
      <h2 className="mb-2 text-lg">{t('answer.basis')}</h2>
      <div className="mb-6">
        <CitationList items={e.citations} />
      </div>
      {e.requires_human_decision && (
        <div className="mb-4">
          <RequiresDecision />
        </div>
      )}
      <h2 className="mb-2 text-lg">{t('answer.nodes')}</h2>
      <div className="mb-4">
        <NodeBadges nodes={e.pipeline_nodes} />
      </div>
      <h2 className="mb-2 text-lg">{t('answer.dims')}</h2>
      <DimensionBadges dims={e.readiness_dimensions} />
      <p className="mt-6 text-xs text-mut">{t('app.disclaimer')}</p>
    </section>
  );
}
