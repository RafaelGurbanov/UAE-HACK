import type { MessageKey } from '../i18n';
import { useT } from '../i18n';
import { PageHeader } from '../components/ui/PageHeader';
import { LoadingBlock } from '../components/ui/States';

/** Phase-1 stand-in: real header + skeleton so layout never shifts when the page lands. */
export function PlannedPage({
  titleKey,
  subtitleKey,
  phase,
}: {
  titleKey: MessageKey;
  subtitleKey?: MessageKey;
  phase: number;
}) {
  const t = useT();
  return (
    <section>
      <PageHeader title={t(titleKey)} subtitle={subtitleKey ? t(subtitleKey) : undefined} />
      <div className="card p-6">
        <p className="mb-5 text-sm text-mut">{t('common.planned', { phase })}</p>
        <LoadingBlock lines={4} />
      </div>
    </section>
  );
}
