import { useEffect, useRef, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ExternalLink, X } from 'lucide-react';
import { useT } from '../../i18n';
import { useLaw } from '../../hooks/useLaw';
import { legalKey } from '../../lib/labels';
import { OFFLINE_MODES, type AskResponse, type Citation } from '../../lib/types';
import { isVerified, VerifyBadge } from '../answer/VerifyBadge';
import { LayerPill } from '../answer/Badges';
import { LoadingBlock } from '../ui/States';

/** Highlights `quote` inside `text` when it is an exact substring. */
function Highlighted({ text, quote }: { text: string; quote: string }) {
  const i = quote ? text.indexOf(quote) : -1;
  if (i < 0) return <>{text}</>;
  return (
    <>
      {text.slice(0, i)}
      <mark className="rounded bg-gold/25 px-0.5 text-tx">{quote}</mark>
      {text.slice(i + quote.length)}
    </>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[7rem_1fr] gap-2 py-1.5">
      <dt className="text-mut">{label}</dt>
      <dd className="text-tx">{children}</dd>
    </div>
  );
}

/** Side drawer on a native <dialog>: focus trap, Esc, inert background for free. */
export function CitationDrawer({
  citation,
  result = null,
  onClose,
}: {
  citation: Citation | null;
  /** The answer this citation belongs to (decides the Verified badge, see isVerified) */
  result?: Pick<AskResponse, 'mode' | 'verification'> | null;
  onClose: () => void;
}) {
  const ok = !!citation && isVerified(result, citation);
  const offline = !!result && OFFLINE_MODES.includes(result.mode);
  // kb/data entries are not documents: there is no article text to load
  const fromData = !!citation?.chunk_id.startsWith('data:');
  const t = useT();
  const ref = useRef<HTMLDialogElement>(null);
  const law = useLaw(fromData ? undefined : citation?.doc_id);
  const article = law.data?.articles.find((a) => a.article === citation?.article);

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (citation && !d.open) d.showModal();
    if (!citation && d.open) d.close();
  }, [citation]);

  return (
    <dialog
      ref={ref}
      aria-labelledby="drawer-title"
      onClose={onClose}
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
      className="drawer m-0 ms-auto h-dvh max-h-none w-full max-w-md border-s border-line bg-bg2 p-0 text-tx backdrop:bg-black/50 backdrop:backdrop-blur-sm"
    >
      {citation && (
        <div className="flex h-full flex-col">
          <header className="flex items-center gap-3 border-b border-line px-5 py-4">
            <span className="pill border border-teal/50 px-2 text-xs font-semibold text-teal-ink">
              {citation.id}
            </span>
            <h2 id="drawer-title" className="text-lg">
              {t('drawer.title')}
            </h2>
            <button
              type="button"
              onClick={onClose}
              className="pill ms-auto inline-flex size-9 items-center justify-center border border-line text-mut hover:text-tx"
              aria-label={t('drawer.close')}
            >
              <X size={18} aria-hidden />
            </button>
          </header>

          <div className="flex-1 space-y-6 overflow-y-auto px-5 py-5">
            <dl className="text-sm">
              <Row label={t('drawer.document')}>
                <span dir="auto">{citation.title}</span>
              </Row>
              {citation.article && (
                <Row label={t('drawer.article')}>
                  {citation.article}
                  {citation.clause ? ` (${citation.clause})` : ''}
                </Row>
              )}
              <Row label={t('drawer.layer')}>
                <LayerPill layer={citation.layer} />
              </Row>
              <Row label={t('drawer.status')}>{t(legalKey(citation.status))}</Row>
              <Row label={t('drawer.language')}>
                {t(
                  citation.language === 'ar'
                    ? 'lang.ar'
                    : citation.language === 'az'
                      ? 'lang.az'
                      : 'lang.en',
                )}
              </Row>
              <Row label={t('drawer.score')}>{citation.score.toFixed(2)}</Row>
            </dl>

            <section>
              <h3 className="mb-2 flex items-center gap-2 font-sans text-sm font-semibold text-mut">
                {t('drawer.quote')}
                <span className="font-normal">
                  <VerifyBadge ok={ok} offline={offline} />
                </span>
              </h3>
              <blockquote dir="auto" className="border-s-2 border-gold ps-3 text-tx">
                {citation.quote}
              </blockquote>
            </section>

            {fromData && <p className="text-xs text-mut">{t('drawer.fromData')}</p>}
            <section hidden={fromData}>
              <h3 className="mb-2 font-sans text-sm font-semibold text-mut">
                {t('drawer.articleText')}
              </h3>
              {law.isLoading && <LoadingBlock lines={4} />}
              {law.isError && <p className="text-sm text-red-ink">{t('drawer.loadError')}</p>}
              {article && (
                <p
                  className="whitespace-pre-line leading-relaxed text-tx"
                  lang={citation.language}
                  dir={citation.language === 'ar' ? 'rtl' : 'ltr'}
                >
                  <Highlighted text={article.text} quote={citation.quote} />
                </p>
              )}
              {citation.layer !== 'global_example' && (
                <p className="mt-3 text-xs text-mut">{t('drawer.authoritative')}</p>
              )}
            </section>
          </div>

          <footer className="flex flex-wrap gap-2 border-t border-line px-5 py-4">
            {!fromData && (
              <Link
                to={`/laws/${encodeURIComponent(citation.doc_id)}${citation.article ? `#art-${citation.article}` : ''}`}
                className="btn-primary text-sm"
                onClick={onClose}
              >
                {t('drawer.fullLaw')}
              </Link>
            )}
            {citation.url ? (
              <a
                href={citation.url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-ghost text-sm"
              >
                {t('drawer.official')} <ExternalLink size={14} aria-hidden />
              </a>
            ) : (
              <span className="self-center text-xs text-mut">{t('drawer.noLink')}</span>
            )}
          </footer>
        </div>
      )}
    </dialog>
  );
}
