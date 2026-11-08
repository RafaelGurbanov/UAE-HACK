import type { ApiClient } from '../client';
import { API_URL } from '../env';
import type { ApiError, AskStreamEvent, StreamEnvelope } from '../types';

export class ApiFailure extends Error {
  constructor(
    public status: number,
    public body: ApiError['error'],
  ) {
    super(body.message);
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiFailure(0, { code: 'network', message: `Backend unreachable at ${API_URL}` });
  }
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as ApiError | null;
    throw new ApiFailure(
      res.status,
      body?.error ?? { code: 'http_error', message: res.statusText },
    );
  }
  const type = res.headers.get('content-type') ?? '';
  return (type.includes('json') ? await res.json() : await res.text()) as T;
}

export const qs = (p: object = {}) => {
  const s = new URLSearchParams(
    Object.entries(p)
      .filter(([, v]) => v !== undefined && v !== '' && v !== null)
      .map(([k, v]) => [k, String(v)]),
  ).toString();
  return s ? `?${s}` : '';
};

/** text/event-stream over fetch (POST-capable, unlike EventSource). Accepts \n, \r\n and \r line endings. */
export async function* readSSE(res: Response): AsyncGenerator<{ event: string; data: string }> {
  const reader = res.body!.pipeThrough(new TextDecoderStream()).getReader();
  let buf = '';
  const parse = (block: string) => {
    let event = 'message';
    const data: string[] = [];
    for (const line of block.split('\n')) {
      if (line.startsWith(':')) continue; // comment / keep-alive ping
      if (line.startsWith('event:')) event = line.slice(6).trim();
      else if (line.startsWith('data:')) data.push(line.slice(5).replace(/^ /, ''));
    }
    return data.length ? { event, data: data.join('\n') } : null;
  };
  for (;;) {
    const { value, done } = await reader.read();
    if (value) buf += value.replace(/\r\n?/g, '\n');
    let i: number;
    while ((i = buf.indexOf('\n\n')) >= 0) {
      const msg = parse(buf.slice(0, i));
      buf = buf.slice(i + 2);
      if (msg) yield msg;
    }
    if (done) {
      const msg = buf.trim() ? parse(buf) : null;
      if (msg) yield msg;
      return;
    }
  }
}

export const httpClient: ApiClient = {
  mode: 'live',
  health: () => req('/health'),
  taxonomy: () => req('/meta/taxonomy'),
  sources: (q) => req(`/sources${qs(q)}`),
  law: (id) => req(`/laws/${encodeURIComponent(id)}`),
  ask: (body) => req('/ask', { method: 'POST', body: JSON.stringify(body) }),
  async *askStream(body, signal) {
    let res: Response;
    try {
      res = await fetch(`${API_URL}/api/ask?stream=true`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
        body: JSON.stringify(body),
        signal,
      });
    } catch (e) {
      if ((e as Error).name === 'AbortError') throw e;
      throw new ApiFailure(0, { code: 'network', message: `Backend unreachable at ${API_URL}` });
    }
    if (!res.ok) {
      const err = (await res.json().catch(() => null)) as ApiError | null;
      throw new ApiFailure(
        res.status,
        err?.error ?? { code: 'http_error', message: res.statusText },
      );
    }
    for await (const m of readSSE(res))
      yield { type: m.event, data: JSON.parse(m.data) } as AskStreamEvent;
  },
  scenarios: () => req('/scenarios'),
  startScenario: (id) => req(`/scenarios/${id}/start`, { method: 'POST' }),
  nextEvent: (id, runId) =>
    req(`/scenarios/${id}/next`, { method: 'POST', body: JSON.stringify({ run_id: runId }) }),
  subscribeScenario(id, runId, onEvent, onError) {
    const es = new EventSource(`${API_URL}/api/scenarios/${id}/stream${qs({ run_id: runId })}`);
    es.onmessage = (m) => onEvent(JSON.parse(m.data) as StreamEnvelope);
    es.onerror = (e) => onError?.(e); // EventSource auto-reconnects with Last-Event-ID
    return () => es.close();
  },
  reviewDecision: (rid, d) =>
    req(`/reviews/${rid}/decision`, { method: 'POST', body: JSON.stringify(d) }),
  gaps: (q) => req(`/gaps${qs(q)}`),
  dataEntries: () => req('/data/entries'),
  dataEntry: (id) => req(`/data/entries/${encodeURIComponent(id)}`),
  audit: (q) => req(`/audit${qs(q)}`),
  exportAudit: (format, runId) =>
    req<string>(`/audit/export${qs({ format, run_id: runId })}`).then((r) =>
      typeof r === 'string' ? r : JSON.stringify(r, null, 2),
    ),
};
