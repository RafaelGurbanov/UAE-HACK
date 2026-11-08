import { Fragment, type ReactNode } from 'react';
import { CircleAlert, Database, FileText, Info } from 'lucide-react';
import { useT } from '../../i18n';
import { OFFLINE_MODES, type AskResponse, type Citation } from '../../lib/types';
import { isVerified, VerifyBadge } from './VerifyBadge';
import { DimensionBadges, LayerPill, NodeBadges, RequiresDecision } from './Badges';

interface Props {
  result: AskResponse;
  onOpenCitation: (c: Citation) => void;
}

/** Replace inline markers like [c1] with small citation buttons. */
export function InlineCitations({
  text,
  citations,
  onOpen,
}: {
  text: string;
  citations: Citation[];
  onOpen?: (c: Citation) => void;
}) {
  const t = useT();
  const parts = text.split(/(\[c\d+\])/g);
  return (
    <>
      {parts.map((p, i) => {
        const m = /^\[(c\d+)\]$/.exec(p);
        const c = m ? citations.find((x) => x.id === m[1]) : undefined;
        if (!m) return <Fragment key={i}>{p}</Fragment>;
        if (!c || !onOpen)
          return (
            <sup key={i} className="text-mut">
              [{m[1]}]
            </sup>
          );
        return (
          <button
            key={i}
            type="button"
            onClick={() => onOpen(c)}
            aria-label={t('answer.openCitation', { id: c.id })}
            className="pill mx-0.5 inline-flex -translate-y-0.5 items-center border border-teal/50 bg-teal/10 px-1.5 text-[11px] font-semibold leading-5 text-teal-ink hover:bg-teal/20"
          >
            {c.id}
          </button>
        );
      })}
    </>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="border-t border-line pt-4">
      <h3 className="mb-2 font-sans text-sm font-semibold text-mut">{title}</h3>
      {children}
    </section>
  );
}

export function AnswerView({ result, onOpenCitation }: Props) {
  const t = useT();
  const a = result.answer!;
  const offline = OFFLINE_MODES.includes(result.mode);
  const passed = !!result.verification?.passed;
  return (
    <article aria-labelledby="answer-title" className="card space-y-5 p-5 sm:p-7">
      <div>
        <h2 id="answer-title" className="mb-3 text-xl">
          {t('answer.short')}
        </h2>
        <p dir="auto" className="text-lg leading-relaxed text-tx">
          <InlineCitations
            text={a.short_answer}
            citations={a.legal_basis}
            onOpen={onOpenCitation}
          />
        </p>
      </div>

      {offline && <OfflineLabel />}

      {!offline && !passed && (
        <p role="note" className="flex items-center gap-2 text-sm text-red-ink">
          <CircleAlert size={15} aria-hidden /> {t('answer.notVerified')}
        </p>
      )}

      {result.requires_human_decision && <RequiresDecision />}

      <Section title={t('answer.basis')}>
        <ul className="grid gap-2 sm:grid-cols-2">
          {a.legal_basis.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                onClick={() => onOpenCitation(c)}
                data-citation={c.id}
                className="card flex w-full flex-col items-start gap-1.5 p-3 text-start transition-shadow hover:shadow-glow-teal"
              >
                <span className="flex w-full items-center gap-2">
                  <span className="pill border border-teal/50 px-1.5 text-[11px] font-semibold text-teal-ink">
                    {c.id}
                  </span>
                  <LayerPill layer={c.layer} />
                  <span className="ms-auto">
                    <VerifyBadge ok={isVerified(result, c)} offline={offline} />
                  </span>
                </span>
                <span dir="auto" className="w-full text-sm text-tx">
                  {c.title}
                </span>
                {c.article && (
                  <span className="text-xs text-mut">{t('answer.article', { a: c.article })}</span>
                )}
              </button>
            </li>
          ))}
        </ul>
        {!!result.verification?.removed.length && (
          <p className="mt-2 text-xs text-red-ink">
            {t('answer.removed')}: {result.verification.removed.join('; ')}
          </p>
        )}
      </Section>

      {a.details && (
        <Section title={t('answer.details')}>
          <p dir="auto" className="text-tx">
            <InlineCitations text={a.details} citations={a.legal_basis} onOpen={onOpenCitation} />
          </p>
        </Section>
      )}

      <Section title={t('answer.limits')}>
        <p dir="auto" className="text-tx">
          {a.status_and_limits}
        </p>
      </Section>

      {a.related.length > 0 && (
        <Section title={t('answer.related')}>
          <ul className="list-inside list-disc text-tx marker:text-mut">
            {a.related.map((r) => (
              <li key={r} dir="auto">
                {r}
              </li>
            ))}
          </ul>
        </Section>
      )}

      <div className="grid gap-5 sm:grid-cols-2">
        {result.pipeline_nodes.length > 0 && (
          <Section title={t('answer.nodes')}>
            <NodeBadges nodes={result.pipeline_nodes} />
          </Section>
        )}
        {result.readiness_dimensions.length > 0 && (
          <Section title={t('answer.dims')}>
            <DimensionBadges dims={result.readiness_dimensions} />
          </Section>
        )}
      </div>

      <p dir="auto" className="border-t border-line pt-4 text-xs text-mut">
        {a.disclaimer}
      </p>
    </article>
  );
}

export function DraftView({ text }: { text: string }) {
  const t = useT();
  return (
    <article className="card p-5 sm:p-7" aria-busy="true">
      <p className="mb-2 text-xs text-mut">{t('answer.draft')}</p>
      <p dir="auto" className="text-lg leading-relaxed text-tx/70">
        <InlineCitations text={text} citations={[]} />
        <span
          aria-hidden
          className="ms-0.5 inline-block h-5 w-1.5 animate-pulse rounded-sm bg-vio/70 align-middle"
        />
      </p>
    </article>
  );
}

export function GeneralAnswerView({ result }: { result: AskResponse }) {
  const t = useT();
  const a = result.answer!;
  return (
    <article aria-labelledby="general-title" className="card space-y-4 border-vio/40 p-5 sm:p-7">
      <p
        role="note"
        className="flex items-center gap-2 rounded-xl border border-vio/50 bg-vio/10 px-3 py-2 text-sm font-medium text-tx"
      >
        <CircleAlert size={16} aria-hidden className="text-vio" /> {t('general.label')}
      </p>
      <h2 id="general-title" className="text-xl">
        {t('general.title')}
      </h2>
      <p dir="auto" className="whitespace-pre-line text-lg leading-relaxed text-tx">
        {a.short_answer}
      </p>
      <p dir="auto" className="border-t border-line pt-4 text-xs text-mut">
        {a.disclaimer}
      </p>
    </article>
  );
}

export function OfflineLabel() {
  const t = useT();
  return (
    <p
      role="note"
      className="pill inline-flex items-center gap-1.5 border border-teal/40 bg-teal/10 px-3 py-1 text-xs font-medium text-teal-ink"
    >
      <Database size={13} aria-hidden /> {t('offline.label')}
    </p>
  );
}

/** Extractive fallback: 1-3 passages shown verbatim, never summarised. */
export function ExtractiveView({ result, onOpenCitation }: Props) {
  const t = useT();
  const a = result.answer!;
  return (
    <article aria-labelledby="extractive-title" className="card space-y-4 p-5 sm:p-7">
      <OfflineLabel />
      <h2 id="extractive-title" className="text-xl">
        {t('extractive.title')}
      </h2>
      <p className="text-sm text-mut">{t('extractive.hint')}</p>
      <ol className="space-y-3">
        {a.legal_basis.map((c) => (
          <li key={c.id} className="card space-y-2 p-4">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="inline-flex items-center gap-1 font-semibold text-tx">
                <FileText size={13} aria-hidden /> {t('extractive.passage')}
              </span>
              <LayerPill layer={c.layer} />
              <span className="ms-auto">
                <VerifyBadge ok={isVerified(result, c)} offline />
              </span>
            </div>
            <p className="text-sm text-mut" dir="auto">
              {c.title}
              {c.article ? ` · ${t('answer.article', { a: c.article })}` : ''}
            </p>
            <blockquote
              dir="auto"
              className="whitespace-pre-line border-s-2 border-gold ps-3 leading-relaxed text-tx"
            >
              {c.quote}
            </blockquote>
            <button type="button" onClick={() => onOpenCitation(c)} className="btn-ghost text-xs">
              {t('extractive.open')}
            </button>
          </li>
        ))}
      </ol>
      <p dir="auto" className="text-xs text-mut">
        {a.status_and_limits}
      </p>
      <p dir="auto" className="border-t border-line pt-4 text-xs text-mut">
        {a.disclaimer}
      </p>
    </article>
  );
}

/** Greetings / small talk / general-mode-offline: a short how-to, not an answer. */
export function GuidanceView({
  result,
  onExample,
}: {
  result: AskResponse;
  onExample?: (q: string) => void;
}) {
  const t = useT();
  const examples = result.suggested_topics ?? [];
  return (
    <article aria-labelledby="guidance-title" className="card space-y-3 border-blu/40 p-5 sm:p-6">
      <h2 id="guidance-title" className="flex items-center gap-2 text-lg">
        <Info size={18} className="text-blu" aria-hidden /> {t('guidance.title')}
      </h2>
      <p dir="auto" className="leading-relaxed text-tx">
        {result.answer?.short_answer}
      </p>
      {examples.length > 0 && (
        <div>
          <p className="mb-2 text-sm text-mut">{t('guidance.examples')}</p>
          <ul className="flex flex-col gap-2">
            {examples.map((q) => (
              <li key={q}>
                <button
                  type="button"
                  dir="auto"
                  onClick={() => onExample?.(q)}
                  className="text-start text-teal-ink underline decoration-line underline-offset-4 hover:decoration-teal"
                >
                  {q}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </article>
  );
}
