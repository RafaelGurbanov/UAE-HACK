import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../lib/api';
import { ApiFailure } from '../lib/http/client';
import type { AskMode, AskResponse, Lang } from '../lib/types';

export type AskPhase = 'idle' | 'retrieving' | 'streaming' | 'verifying' | 'done' | 'error';

export interface AskState {
  phase: AskPhase;
  question: string;
  draft: string;
  retrieved: number;
  result: AskResponse | null;
  error: string | null;
  /** network | llm_unavailable | kb_empty | http_error | … */
  errorCode: string | null;
  mode: AskMode;
}

const initial: AskState = {
  phase: 'idle',
  question: '',
  draft: '',
  retrieved: 0,
  result: null,
  error: null,
  errorCode: null,
  mode: 'grounded',
};

/** Streams POST /api/ask (or the mock). Only `final` is shown as the verified answer. */
export function useAskStream() {
  const [state, setState] = useState<AskState>(initial);
  const ctrl = useRef<AbortController | null>(null);
  const conversationId = useRef<string | undefined>(undefined);

  useEffect(() => () => ctrl.current?.abort(), []);

  const ask = useCallback(async (question: string, mode: AskMode = 'grounded', language?: Lang) => {
    ctrl.current?.abort();
    const c = new AbortController();
    ctrl.current = c;
    setState({ ...initial, phase: 'retrieving', question, mode });
    try {
      for await (const ev of api.askStream(
        { question, mode, language, conversation_id: conversationId.current },
        c.signal,
      )) {
        if (c.signal.aborted) return;
        switch (ev.type) {
          case 'retrieval':
            setState((s) => ({ ...s, retrieved: ev.data.chunks.length }));
            break;
          case 'token':
            setState((s) => ({ ...s, phase: 'streaming', draft: s.draft + ev.data.text }));
            break;
          case 'verification':
            setState((s) => ({ ...s, phase: 'verifying' }));
            break;
          case 'final':
            conversationId.current = ev.data.conversation_id;
            setState((s) => ({ ...s, phase: 'done', result: ev.data }));
            break;
          case 'error':
            setState((s) => ({
              ...s,
              phase: 'error',
              error: ev.data.message,
              errorCode: ev.data.code,
            }));
            break;
        }
      }
    } catch (e) {
      if ((e as Error).name === 'AbortError') return;
      setState((s) => ({
        ...s,
        phase: 'error',
        error: e instanceof Error ? e.message : String(e),
        errorCode: e instanceof ApiFailure ? e.body.code : 'unknown',
      }));
    }
  }, []);

  const reset = useCallback(() => {
    ctrl.current?.abort();
    setState(initial);
  }, []);
  return { ...state, ask, reset };
}
