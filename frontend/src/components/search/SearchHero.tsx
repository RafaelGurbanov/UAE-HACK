import { useEffect, useId, useState, type ReactNode } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ArrowRight, Search } from 'lucide-react';
import { useT, type MessageKey } from '../../i18n';

const EXAMPLES: MessageKey[] = ['search.ex1', 'search.ex2', 'search.ex3', 'search.ex4'];
export const TOPICS: MessageKey[] = [
  'topic.childrenData',
  'topic.consent',
  'topic.iap',
  'topic.adsMinors',
  'topic.crossBorder',
  'topic.counsellor',
];

interface Props {
  busy: boolean;
  onAsk: (q: string) => void;
  children?: ReactNode;
}

export function SearchHero({ busy, onAsk, children }: Props) {
  const t = useT();
  const id = useId();
  const [q, setQ] = useState('');
  const [ex, setEx] = useState(0);
  const [paused, setPaused] = useState(false);
  const [hint, setHint] = useState(false);

  useEffect(() => {
    if (paused) return;
    const h = setInterval(() => setEx((i) => (i + 1) % EXAMPLES.length), 4500);
    return () => clearInterval(h);
  }, [paused]);

  const example = t(EXAMPLES[ex]!);
  const submit = (text: string) => {
    const v = text.trim();
    if (busy) return;
    if (v.length < 3) {
      setHint(true);
      return;
    }
    setHint(false);
    setQ(v);
    onAsk(v);
  };

  return (
    <section className="mx-auto max-w-3xl pt-4 text-center sm:pt-10">
      <h1 className="text-4xl leading-tight text-tx sm:text-6xl">{t('search.title')}</h1>
      <p className="mx-auto mt-4 max-w-2xl text-mut sm:text-lg">{t('search.subtitle')}</p>

      <form
        role="search"
        onSubmit={(e) => {
          e.preventDefault();
          submit(q);
        }}
        className="card mt-8 flex items-center gap-2 p-2 ps-4 transition-shadow focus-within:shadow-glow-vio sm:gap-3"
        style={{ borderRadius: 'var(--radius-pill)' }}
      >
        <Search aria-hidden className="shrink-0 text-vio" size={20} />
        <label htmlFor={`${id}-q`} className="sr-only">
          {t('search.label')}
        </label>
        <input
          id={`${id}-q`}
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            if (hint) setHint(false);
          }}
          aria-describedby={hint ? `${id}-hint` : undefined}
          onFocus={() => setPaused(true)}
          onBlur={() => setPaused(q.length > 0)}
          placeholder={t('search.placeholder')}
          autoComplete="off"
          className="min-w-0 flex-1 bg-transparent py-2 text-base text-tx outline-none placeholder:text-mut focus-visible:outline-none"
        />
        <button type="submit" disabled={busy} className="btn-primary shrink-0">
          {t('search.submit')} <ArrowRight size={16} aria-hidden className="rtl:rotate-180" />
        </button>
      </form>

      {hint && (
        <p id={`${id}-hint`} role="status" className="mt-3 text-sm text-amb-ink">
          {t('search.tooShort')}
        </p>
      )}

      {children}

      <div className="mt-4 flex min-h-12 items-center justify-center gap-2 text-sm text-mut sm:min-h-8">
        <span className="shrink-0">{t('search.try')}:</span>
        <AnimatePresence mode="wait" initial={false}>
          <motion.button
            key={ex}
            type="button"
            onClick={() => submit(example)}
            onMouseEnter={() => setPaused(true)}
            onMouseLeave={() => setPaused(false)}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.25 }}
            className="text-start text-teal-ink underline decoration-line underline-offset-4 hover:decoration-teal"
          >
            “{example}”
          </motion.button>
        </AnimatePresence>
      </div>

      <ul aria-label={t('search.topics')} className="mt-5 flex flex-wrap justify-center gap-2">
        {TOPICS.map((k) => (
          <li key={k}>
            <button
              type="button"
              onClick={() => submit(t(k))}
              disabled={busy}
              className="btn-ghost text-sm disabled:opacity-50"
            >
              {t(k)}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
