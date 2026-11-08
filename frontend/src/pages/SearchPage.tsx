import { useEffect, useRef, useState } from 'react';
import { useReducedMotion } from 'framer-motion';
import { RotateCcw } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { useT } from '../i18n';
import { useAskStream } from '../hooks/useAskStream';
import type { AskMode, Citation } from '../lib/types';
import { PipelineMap } from '../components/pipeline/PipelineMap';
import { SearchHero } from '../components/search/SearchHero';
import { ModeToggle } from '../components/search/ModeToggle';
import {
  AnswerView,
  DraftView,
  ExtractiveView,
  GeneralAnswerView,
  GuidanceView,
} from '../components/answer/AnswerView';
import { useHealth } from '../hooks/useHealth';
import { NoSourceNotice } from '../components/answer/NoSourceNotice';
import { CitationDrawer } from '../components/citation/CitationDrawer';
import { BackendStatus } from '../components/live/BackendStatus';
import { LiveProblem, type ProblemKind } from '../components/live/LiveProblem';
import { ErrorState, LoadingBlock } from '../components/ui/States';

const PROBLEMS: ProblemKind[] = ['network', 'llm_unavailable', 'kb_empty'];

export function SearchPage() {
  const t = useT();
  const s = useAskStream();
  const qc = useQueryClient();
  const health = useHealth();
  const offlineMode = health.data?.answer_mode === 'offline';
  const [mode, setMode] = useState<AskMode>('grounded');
  const [citation, setCitation] = useState<Citation | null>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  const busy = s.phase === 'retrieving' || s.phase === 'streaming' || s.phase === 'verifying';
  const result = s.phase === 'done' ? s.result : null;
  const ask = (q: string) => void s.ask(q, mode);

  useEffect(() => {
    const el = resultsRef.current;
    if (s.phase !== 'retrieving' || !el?.scrollIntoView) return;
    const r = el.getBoundingClientRect();
    if (r.top > window.innerHeight * 0.6)
      el.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
  }, [s.phase, reduce]);

  // a failed request may mean the backend state changed: refresh the status banner
  useEffect(() => {
    if (s.phase === 'error') void qc.invalidateQueries({ queryKey: ['health'] });
  }, [s.phase, qc]);

  const status =
    s.phase === 'retrieving'
      ? s.mode === 'general'
        ? t('general.title')
        : t('status.retrieving')
      : s.phase === 'streaming'
        ? s.mode === 'general'
          ? t('general.title')
          : t('status.streaming', { n: s.retrieved })
        : s.phase === 'verifying'
          ? t('status.verifying')
          : result?.outcome === 'no_source'
            ? t('status.refused')
            : result?.mode === 'offline_json' || result?.mode === 'extractive'
              ? t('offline.label')
              : result?.outcome === 'answered'
                ? t('status.done', {
                    v: result.verification?.verified ?? 0,
                    c: result.verification?.checked ?? 0,
                  })
                : '';

  const problem =
    s.phase === 'error' && PROBLEMS.includes(s.errorCode as ProblemKind)
      ? (s.errorCode as ProblemKind)
      : null;

  return (
    <div className="space-y-8">
      <SearchHero busy={busy} onAsk={ask}>
        <ModeToggle
          mode={mode}
          onChange={setMode}
          disabled={busy}
          generalAvailable={!offlineMode}
        />
        <div className="mt-4">
          <BackendStatus />
        </div>
      </SearchHero>

      <PipelineMap
        active={result?.outcome === 'answered' ? result.pipeline_nodes : []}
        pulseKey={result?.answer_id}
      />

      <div ref={resultsRef} className="min-h-40 scroll-mt-24 space-y-3">
        <div className="flex items-center justify-between gap-3">
          <p role="status" aria-live="polite" className="text-sm text-mut">
            {status}
          </p>
          {s.phase !== 'idle' && !busy && (
            <button type="button" onClick={s.reset} className="btn-ghost text-xs">
              <RotateCcw size={13} aria-hidden /> {t('answer.again')}
            </button>
          )}
        </div>
        {s.question && s.phase !== 'idle' && (
          <p dir="auto" className="text-sm text-tx">
            “{s.question}”
          </p>
        )}

        {s.phase === 'retrieving' && (
          <div className="card p-6">
            <LoadingBlock lines={4} />
          </div>
        )}
        {(s.phase === 'streaming' || s.phase === 'verifying') && <DraftView text={s.draft} />}
        {problem && (
          <LiveProblem
            kind={problem}
            message={s.error ?? undefined}
            onRetry={() => ask(s.question)}
          />
        )}
        {s.phase === 'error' && !problem && (
          <ErrorState message={s.error ?? undefined} onRetry={() => ask(s.question)} />
        )}
        {result?.outcome === 'answered' && result.answer && result.mode === 'extractive' && (
          <ExtractiveView result={result} onOpenCitation={setCitation} />
        )}
        {result?.outcome === 'answered' && result.answer && result.mode !== 'extractive' && (
          <AnswerView result={result} onOpenCitation={setCitation} />
        )}
        {result?.outcome === 'guidance' && <GuidanceView result={result} onExample={ask} />}
        {result?.outcome === 'general' && result.answer && <GeneralAnswerView result={result} />}
        {result?.outcome === 'no_source' && <NoSourceNotice result={result} onTopic={ask} />}
      </div>

      <CitationDrawer citation={citation} result={result} onClose={() => setCitation(null)} />
    </div>
  );
}
