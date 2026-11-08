import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from 'recharts';
import { useT, type MessageKey } from '../i18n';
import { api } from '../lib/api';
import { dimKey } from '../lib/labels';
import type { GapType, PolicyGap, ReadinessDimension } from '../lib/types';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorState, LoadingBlock } from '../components/ui/States';
import { CitationList, SeverityPill } from '../components/ui/Bits';
import { NodeBadges } from '../components/answer/Badges';

const TYPES: GapType[] = [
  'unclear_responsibility',
  'missing_standard',
  'legislative_gap',
  'coordination_problem',
  'objective_conflict',
];

export function GapsPage() {
  const t = useT();
  const [type, setType] = useState<GapType | null>(null);
  const q = useQuery({
    queryKey: ['gaps', type],
    queryFn: () => api.gaps(type ? { gap_type: type } : {}),
  });
  const radar = Object.entries(q.data?.readiness_radar ?? {}).map(([d, v]) => ({
    dim: t(dimKey(d as ReadinessDimension)),
    value: v ?? 0,
  }));
  return (
    <section>
      <PageHeader title={t('page.gaps.title')} subtitle={t('page.gaps.subtitle')} />
      <div role="group" aria-label={t('gaps.filter')} className="mb-6 flex flex-wrap gap-2">
        {[null, ...TYPES].map((g) => (
          <button
            key={g ?? 'all'}
            type="button"
            aria-pressed={type === g}
            onClick={() => setType(g)}
            className={`pill border px-3 py-1.5 text-sm ${type === g ? 'border-teal bg-teal/10 text-tx shadow-glow-teal' : 'border-line text-mut hover:text-tx'}`}
          >
            {g ? t(`gap.${g}` as MessageKey) : t('gaps.all')}
          </button>
        ))}
      </div>
      {q.isLoading && <LoadingBlock lines={5} />}
      {q.isError && (
        <ErrorState message={(q.error as Error).message} onRetry={() => void q.refetch()} />
      )}
      {q.data && (
        <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
          <div className="space-y-4">
            {q.data.gaps.length === 0 && <EmptyState title={t('gaps.empty')} />}
            {q.data.gaps.map((g) => (
              <GapCard key={g.id} g={g} />
            ))}
          </div>
          <aside className="card h-fit p-4 lg:sticky lg:top-20">
            <h2 className="mb-1 text-lg">{t('gaps.radar')}</h2>
            <p className="mb-2 text-xs text-mut">{t('gaps.radarHint')}</p>
            <div className="h-72" data-testid="radar">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radar} outerRadius="62%">
                  <PolarGrid stroke="var(--line)" />
                  <PolarAngleAxis
                    dataKey="dim"
                    tick={{ fill: 'var(--mut)', fontSize: 9 }}
                    tickFormatter={(s: string) => (s.length > 22 ? `${s.slice(0, 20)}…` : s)}
                  />
                  <PolarRadiusAxis domain={[0, 1]} tick={false} axisLine={false} />
                  <Radar
                    dataKey="value"
                    stroke="var(--vio)"
                    fill="var(--vio)"
                    fillOpacity={0.35}
                    isAnimationActive={false}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            <ul className="mt-2 space-y-0.5 text-[11px] text-mut">
              {radar.map((r) => (
                <li key={r.dim} className="flex justify-between gap-2">
                  <span>{r.dim}</span>
                  <span className="font-mono">{Math.round(r.value * 100)}%</span>
                </li>
              ))}
            </ul>
          </aside>
        </div>
      )}
    </section>
  );
}

function GapCard({ g }: { g: PolicyGap }) {
  const t = useT();
  const uaeUnverified =
    !g.uae_says.citations.length || g.uae_says.citations.some((c) => !c.verified);
  return (
    <article
      className="card space-y-4 p-4 sm:p-5"
      aria-labelledby={`gap-${g.id}`}
      data-gap-type={g.gap_type}
    >
      <header className="flex flex-wrap items-center gap-2">
        <h2 id={`gap-${g.id}`} className="w-full text-lg sm:w-auto sm:flex-1">
          {g.title}
        </h2>
        <span className="pill border border-vio/40 bg-vio/10 px-2 py-0.5 text-[11px] text-tx">
          {t(`gap.${g.gap_type}` as MessageKey)}
        </span>
        <SeverityPill level={g.severity} />
      </header>
      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-teal/30 p-3">
          <h3 className="mb-1 font-sans text-sm font-semibold text-teal-ink">{t('gaps.uae')}</h3>
          {uaeUnverified && (
            <p className="mb-1 text-xs font-medium text-amb-ink">{t('gaps.sourceToVerify')}</p>
          )}
          <p dir="auto" className="mb-2 text-sm text-tx">
            {g.uae_says.statement}
          </p>
          <CitationList items={g.uae_says.citations} />
        </div>
        <div className="rounded-xl border border-vio/30 p-3">
          <h3 className="mb-1 font-sans text-sm font-semibold text-tx">{t('gaps.global')}</h3>
          <p dir="auto" className="mb-2 text-sm text-tx">
            {g.global_example_says.statement}
          </p>
          <CitationList items={g.global_example_says.citations} />
        </div>
        <div className="rounded-xl border border-gold/40 bg-gold/5 p-3">
          <h3 className="mb-1 font-sans text-sm font-semibold text-gold-ink">{t('gaps.gap')}</h3>
          <p dir="auto" className="mb-2 text-sm text-tx">
            {g.gap_analysis}
          </p>
          <p className="text-xs text-mut">
            <b>{t('gaps.recommendation')}:</b> {g.recommendation}
          </p>
        </div>
      </div>
      <NodeBadges nodes={g.pipeline_nodes} />
    </article>
  );
}
