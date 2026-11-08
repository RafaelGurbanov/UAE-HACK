import { useT, type MessageKey } from '../i18n';
import { NODE_DIMENSIONS, PIPELINE, dimKey, nodeKey } from '../lib/labels';
import { PageHeader } from '../components/ui/PageHeader';

export function AboutPage() {
  const t = useT();
  return (
    <section className="space-y-8">
      <PageHeader title={t('page.about.title')} subtitle={t('page.about.subtitle')} />
      <div className="card space-y-3 p-5">
        <h2 className="text-xl">{t('about.howTitle')}</h2>
        <ol className="list-inside list-decimal space-y-1 text-sm text-tx">
          {(['about.how1', 'about.how2', 'about.how3', 'about.how4'] as MessageKey[]).map((k) => (
            <li key={k}>{t(k)}</li>
          ))}
        </ol>
      </div>
      <div className="card overflow-x-auto p-0">
        <h2 className="px-5 pt-5 text-xl">{t('about.pipelineTitle')}</h2>
        <table className="mt-3 w-full text-sm">
          <thead className="border-b border-line">
            <tr>
              <th className="px-5 py-2 text-start text-xs text-mut">{t('about.node')}</th>
              <th className="px-5 py-2 text-start text-xs text-mut">{t('about.component')}</th>
              <th className="px-5 py-2 text-start text-xs text-mut">{t('pipeline.dims')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {PIPELINE.map((n) => (
              <tr key={n}>
                <td className="px-5 py-2 font-mono font-semibold text-gold-ink">{n}</td>
                <td className="px-5 py-2">{t(nodeKey(n))}</td>
                <td className="px-5 py-2 text-xs text-mut">
                  {NODE_DIMENSIONS[n].map((d) => t(dimKey(d))).join(' · ')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="card space-y-2 p-5">
        <h2 className="text-xl">{t('about.limitsTitle')}</h2>
        <ul className="list-inside list-disc space-y-1 text-sm text-tx">
          {(['about.limit1', 'about.limit2', 'about.limit3', 'about.limit4'] as MessageKey[]).map(
            (k) => (
              <li key={k}>{t(k)}</li>
            ),
          )}
        </ul>
        <p className="pt-2 text-xs text-mut">{t('app.disclaimer')}</p>
      </div>
    </section>
  );
}
