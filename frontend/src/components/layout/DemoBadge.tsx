import { FlaskConical } from 'lucide-react';
import { MOCK } from '../../lib/env';
import { useT } from '../../i18n';

export function DemoBadge() {
  const t = useT();
  if (!MOCK) return null;
  return (
    <span
      role="note"
      title={t('app.demoBadgeHint')}
      className="inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap pill border border-gold/50 bg-gold/10 px-2 py-1 text-xs sm:px-2.5 font-medium text-gold-ink"
    >
      <FlaskConical size={13} aria-hidden />
      {t('app.demoBadge')}
      <span className="sr-only">. {t('app.demoBadgeHint')}</span>
    </span>
  );
}
