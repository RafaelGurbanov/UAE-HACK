import { useId, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { useT } from '../../i18n';
import { NODE_DIMENSIONS, PIPELINE, dimKey, nodeKey, nodeShortKey } from '../../lib/labels';
import type { PipelineNode } from '../../lib/types';

interface Props {
  active: PipelineNode[];
  /** Changes whenever a new answer/event arrives, to replay the highlight. */
  pulseKey?: string | number;
  className?: string;
}

/**
 * The signature element: Y.3172 pipeline SRC → C → PP → M → P → D → SINK.
 * HTML (not canvas) so it stays crisp, keyboard-accessible and flips in RTL.
 */
export function PipelineMap({ active, pulseKey, className = '' }: Props) {
  const t = useT();
  const reduce = useReducedMotion();
  const [selected, setSelected] = useState<PipelineNode | null>(null);
  const detailId = useId();
  const shown = selected ?? active[0] ?? null;

  return (
    <section aria-labelledby={`${detailId}-title`} className={`card p-4 sm:p-6 ${className}`}>
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
        <h2 id={`${detailId}-title`} className="text-lg">
          {t('pipeline.title')}
        </h2>
        <p className="text-xs text-mut" aria-live="polite">
          {active.length ? `${t('pipeline.touched')}: ${active.join(', ')}` : t('pipeline.hint')}
        </p>
      </div>

      <div className="relative">
        {/* connecting line + travelling pulse, centred on the node row */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-[7%] top-5 h-px bg-line sm:top-7"
        >
          {!reduce && (
            <span
              key={pulseKey}
              className="pipeline-pulse absolute top-1/2 size-2 -translate-y-1/2 rounded-full bg-teal shadow-glow-teal"
            />
          )}
        </div>

        <ol className="relative grid grid-cols-7 gap-1">
          {PIPELINE.map((n, i) => {
            const lit = active.includes(n);
            const isShown = shown === n;
            return (
              <li key={n} className="flex flex-col items-center gap-2 text-center">
                <motion.button
                  type="button"
                  onClick={() => setSelected((s) => (s === n ? null : n))}
                  aria-pressed={selected === n}
                  aria-describedby={isShown ? detailId : undefined}
                  aria-label={`${n}: ${t(nodeKey(n))}. ${lit ? t('pipeline.touched') : t('pipeline.idle')}`}
                  data-node={n}
                  data-active={lit || undefined}
                  className={`relative flex size-10 items-center justify-center rounded-full border text-[11px] font-semibold transition-colors sm:size-14 sm:text-sm ${
                    lit
                      ? 'border-gold bg-[color-mix(in_srgb,var(--gold)_18%,var(--bg2))] text-gold-ink shadow-glow-gold'
                      : 'border-line-strong bg-bg2 text-mut hover:text-tx'
                  } ${selected === n ? 'ring-2 ring-vio/70 ring-offset-2 ring-offset-[var(--bg)]' : ''}`}
                  initial={false}
                  animate={lit && !reduce ? { scale: [1, 1.12, 1] } : { scale: 1 }}
                  transition={{ duration: 0.6, delay: reduce ? 0 : i * 0.08 }}
                  key={`${n}-${lit ? pulseKey : 'idle'}`}
                >
                  {n}
                </motion.button>
                <span
                  className={`text-[10px] leading-tight sm:text-xs ${lit ? 'text-tx' : 'text-mut'}`}
                >
                  {t(nodeShortKey(n))}
                </span>
              </li>
            );
          })}
        </ol>
      </div>

      <div id={detailId} className="mt-4 min-h-12 border-t border-line pt-3 text-sm">
        {shown ? (
          <p>
            <span className="font-semibold text-tx">
              {shown}: {t(nodeKey(shown))}
            </span>
            <span className="text-mut">
              {' '}
              · {t('pipeline.dims')}: {NODE_DIMENSIONS[shown].map((d) => t(dimKey(d))).join('; ')}
            </span>
          </p>
        ) : (
          <p className="text-mut">{t('pipeline.hint')}</p>
        )}
      </div>
    </section>
  );
}
