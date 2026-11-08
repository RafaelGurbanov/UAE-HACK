// The ONE typed interface the UI depends on. Two implementations:
//   lib/http/client.ts  -> FastAPI backend (REST + SSE), see docs/api.md
//   lib/mock/client.ts  -> local fixtures + scripted scenario replay
// The frontend never holds secrets and never calls an LLM.
import type {
  AskRequest,
  AskResponse,
  AskStreamEvent,
  AuditQuery,
  AuditResponse,
  DataEntriesResponse,
  DataEntryDetail,
  GapsResponse,
  Health,
  LawDetail,
  NextEventResponse,
  ReviewDecision,
  ReviewDecisionResponse,
  ScenarioSummary,
  SourcesQuery,
  SourcesResponse,
  StartScenarioResponse,
  StreamEnvelope,
  Taxonomy,
} from './types';

export type Unsubscribe = () => void;

export interface ApiClient {
  readonly mode: 'mock' | 'live';
  health(): Promise<Health>;
  taxonomy(): Promise<Taxonomy>;
  sources(q?: SourcesQuery): Promise<SourcesResponse>;
  law(docId: string): Promise<LawDetail>;
  ask(body: AskRequest): Promise<AskResponse>;
  askStream(body: AskRequest, signal?: AbortSignal): AsyncGenerator<AskStreamEvent>;
  scenarios(): Promise<ScenarioSummary[]>;
  startScenario(id: string): Promise<StartScenarioResponse>;
  nextEvent(id: string, runId: string): Promise<NextEventResponse>;
  subscribeScenario(
    id: string,
    runId: string,
    onEvent: (e: StreamEnvelope) => void,
    onError?: (e: unknown) => void,
  ): Unsubscribe;
  reviewDecision(reviewId: string, d: ReviewDecision): Promise<ReviewDecisionResponse>;
  gaps(q?: { gap_type?: string; domain?: string }): Promise<GapsResponse>;
  audit(q?: AuditQuery): Promise<AuditResponse>;
  dataEntries(): Promise<DataEntriesResponse>;
  dataEntry(id: string): Promise<DataEntryDetail>;
  /** Returns the export as text (works identically in mock and live; UI makes the Blob). */
  exportAudit(format: 'json' | 'jsonl', runId?: string): Promise<string>;
}
