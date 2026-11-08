import { useT } from '../../i18n';
import type { GapCitation } from '../../lib/types';
import { LayerPill } from '../answer/Badges';
import { VerifyBadge } from '../answer/VerifyBadge';

/** Confidence 0..1 as a ring with the percentage in the middle. */
export function ConfidenceRing({ value, size = 44 }: { value: number; size?: number }) {
  const t = useT();
  const r = (size - 6) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  const color = pct >= 75 ? 'var(--teal)' : pct >= 50 ? 'var(--amb)' : 'var(--red)';
  return (
    <svg
      width={size}
      height={size}
      role="img"
      aria-label={t('scenario.confidence', { n: pct })}
      className="shrink-0"
    >
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--line)" strokeWidth="4" />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth="4"
        strokeLinecap="round"
        strokeDasharray={`${(c * pct) / 100} ${c}`}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
      <text
        x="50%"
        y="50%"
        dominantBaseline="central"
        textAnchor="middle"
        fontSize="11"
        fill="var(--tx)"
      >
        {pct}%
      </text>
    </svg>
  );
}

const SEV: Record<string, string> = {
  info: 'border-blu/50 bg-blu/10 text-blu-ink',
  warning: 'border-amb/50 bg-amb/10 text-amb-ink',
  critical: 'border-red/50 bg-red/10 text-red-ink',
  low: 'border-blu/50 bg-blu/10 text-blu-ink',
  medium: 'border-amb/50 bg-amb/10 text-amb-ink',
  high: 'border-red/50 bg-red/10 text-red-ink',
};

export function SeverityPill({ level }: { level: string }) {
  const t = useT();
  return (
    <span className={`pill border px-2 py-0.5 text-[11px] font-medium ${SEV[level] ?? ''}`}>
      {t(`severity.${level}` as never)}
    </span>
  );
}

/** Citations from kb/data or gap files: "Verified" only when the citation itself is verified. */
export function CitationList({ items }: { items: GapCitation[] }) {
  const t = useT();
  if (!items.length) return <p className="text-xs text-amb-ink">{t('answer.toVerify')}</p>;
  return (
    <ul className="space-y-1.5">
      {items.map((c, i) => (
        <li key={i} className="flex flex-wrap items-center gap-2 text-xs">
          <LayerPill layer={c.layer} />
          <span dir="auto" className="text-tx">
            {c.law}
          </span>
          {c.article && c.article !== c.law && (
            <span className="text-mut" dir="auto">
              · {c.article}
            </span>
          )}
          <span className="ms-auto">
            <VerifyBadge ok={c.verified} offline />
          </span>
        </li>
      ))}
    </ul>
  );
}
