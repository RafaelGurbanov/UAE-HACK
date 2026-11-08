// Mirrors backend/app/api/schemas.py — change the backend first, then this file.

export type Lang = 'en' | 'ar' | 'az';
export type PipelineNode = 'SRC' | 'C' | 'PP' | 'M' | 'P' | 'D' | 'SINK';
export type ReadinessDimension =
  | 'open_data_open_source'
  | 'generative_ai_content_ecosystem'
  | 'contextualisation_regional_development'
  | 'domain_integration_cross_domain'
  | 'human_interaction_supervision'
  | 'ai_policy_implementation'
  | 'ai_social_inclusion'
  | 'digital_infrastructure_energy';
export type KBLayer = 'uae_federal' | 'emirate' | 'global_example';
export type LegalStatus = 'in_force' | 'amended' | 'repealed' | 'not_legislation' | 'unknown';
export type AgentId =
  | 'legal_adviser'
  | 'data_protection'
  | 'education'
  | 'consumer_protection'
  | 'ai_ethics'
  | 'coordinator'
  | 'gap_analyst';
export type GapType =
  | 'unclear_responsibility'
  | 'missing_standard'
  | 'legislative_gap'
  | 'coordination_problem'
  | 'objective_conflict';
export type Domain = string;

export interface ApiError {
  error: { code: string; message: string; details?: Record<string, unknown> | null };
}

export interface Health {
  status: 'ok' | 'degraded';
  version: string;
  llm_provider: string;
  llm_model: string;
  llm_configured: boolean;
  embedding_provider: string;
  embedding_model: string;
  kb_documents: number;
  kb_chunks: number;
  index_chunks: number;
  answer_mode?: 'offline' | 'llm';
  data_entries?: number;
  data_errors?: string[];
  semantic_search?: boolean;
  audit_entries: number;
  problems: string[];
}

export interface TaxonomyItem {
  id: string;
  label: string;
}
export interface Taxonomy {
  pipeline_nodes: TaxonomyItem[];
  readiness_dimensions: TaxonomyItem[];
  layers: KBLayer[];
  gap_types: GapType[];
  domains: Domain[];
  agents: AgentId[];
}

export interface SourceDocument {
  doc_id: string;
  title: string;
  title_ar: string | null;
  issuing_body: string;
  law_number: string | null;
  year: number | null;
  status: LegalStatus;
  layer: KBLayer;
  language: Lang;
  translation_of: string | null;
  amends: string[];
  amended_by: string[];
  domains: Domain[];
  url: string;
  retrieved_at: string | null;
  verified: boolean;
  chunk_count: number;
}

export interface SourcesResponse {
  documents: SourceDocument[];
  coverage: { layer: KBLayer; domain: Domain; documents: number }[];
  total_documents: number;
  total_chunks: number;
}

export interface Article {
  article: string;
  heading: string | null;
  chapter: string | null;
  text: string;
  chunk_ids: string[];
  amended: boolean;
}
export interface LawDetail {
  document: SourceDocument;
  articles: Article[];
  translations: string[];
}

export type AskMode = 'grounded' | 'general';
/** What actually produced the answer (response only). */
export type AnswerMode = AskMode | 'offline_json' | 'extractive' | 'no_source' | 'guidance';
export const OFFLINE_MODES: AnswerMode[] = ['offline_json', 'extractive'];

export interface AskRequest {
  question: string;
  mode?: AskMode;
  language?: Lang;
  conversation_id?: string;
  agent?: AgentId;
  filters?: { layers?: KBLayer[]; include_repealed?: boolean; domains?: Domain[] };
}

export interface Citation {
  id: string;
  chunk_id: string;
  doc_id: string;
  title: string;
  law_number: string | null;
  year: number | null;
  article: string | null;
  clause: string | null;
  quote: string;
  url: string;
  layer: KBLayer;
  status: LegalStatus;
  language: Lang;
  score: number;
  verified: boolean;
}

export interface AnswerSections {
  short_answer: string;
  legal_basis: Citation[];
  details: string | null;
  status_and_limits: string;
  related: string[];
  disclaimer: string;
}

export interface AskResponse {
  answer_id: string;
  conversation_id: string;
  outcome: 'answered' | 'no_source' | 'general' | 'guidance';
  mode: AnswerMode;
  matched_entry?: string | null;
  language: Lang;
  answer: AnswerSections | null;
  no_source_message: string | null;
  suggested_topics: string[];
  pipeline_nodes: PipelineNode[];
  readiness_dimensions: ReadinessDimension[];
  verification: VerificationReport | null;
  requires_human_decision: boolean;
  audit_id: string;
}

export interface VerificationReport {
  /** True only if at least one citation survived and none failed. Badges show "Verified" only then. */
  passed: boolean;
  checked: number;
  verified: number;
  removed: string[];
  warnings: string[];
}

export type AskStreamEvent =
  | {
      type: 'retrieval';
      data: {
        chunks: { chunk_id: string; doc_id: string; article: string | null; score: number }[];
        best_score?: number;
        threshold?: number;
      };
    }
  | { type: 'token'; data: { text: string } }
  | { type: 'verification'; data: AskResponse['verification'] }
  | { type: 'final'; data: AskResponse }
  | { type: 'error'; data: ApiError['error'] };

export interface ScenarioSummary {
  id: string;
  title: string;
  description: string;
  controversial: boolean;
  total_events: number;
}

export interface ScenarioEvent {
  id: string;
  step: number;
  at: string;
  title: string;
  description: string;
  severity: 'info' | 'warning' | 'critical';
  visible_to: AgentId[];
  pipeline_nodes: PipelineNode[];
}

export type StreamType =
  | 'run_started'
  | 'event_released'
  | 'agent_status'
  | 'agent_step'
  | 'agent_assessment'
  | 'conflict_detected'
  | 'coordinator_recommendation'
  | 'human_review_required'
  | 'pipeline_highlight'
  | 'run_completed'
  | 'review_recorded'
  | 'error';

export interface StreamEnvelope<T = Record<string, unknown>> {
  type: StreamType;
  run_id: string;
  seq: number;
  ts: string;
  data: T;
}

export interface GapCitation {
  law: string;
  article: string;
  layer: KBLayer;
  url: string;
  quote: string;
  verified: boolean;
}
export interface GapSide {
  statement: string;
  citations: GapCitation[];
}
export interface PolicyGap {
  id: string;
  title: string;
  gap_type: GapType;
  domain: Domain;
  uae_says: GapSide;
  global_example_says: GapSide;
  gap_analysis: string;
  recommendation: string;
  severity: 'low' | 'medium' | 'high';
  pipeline_nodes: PipelineNode[];
  readiness_dimensions: ReadinessDimension[];
  audit_id?: string | null;
}
export interface GapsResponse {
  gaps: PolicyGap[];
  readiness_radar: Partial<Record<ReadinessDimension, number>>;
}

export interface AuditEntry {
  audit_id: string;
  timestamp: string;
  kind: 'ask' | 'agent' | 'coordinator' | 'gap' | 'scenario_event' | 'human_decision' | 'system';
  mode?: string | null;
  outcome?: string | null;
  matched_entry?: string | null;
  score?: number | null;
  agent: AgentId | null;
  run_id: string | null;
  input_event: string;
  retrieved_chunks: {
    chunk_id: string;
    doc_id: string;
    article: string | null;
    url: string;
    score: number;
  }[];
  reasoning_steps: string[];
  recommendation: string | null;
  citations: string[];
  confidence: number | null;
  pipeline_nodes: PipelineNode[];
  readiness_dimensions: ReadinessDimension[];
  requires_human_decision: boolean;
  llm: Record<string, unknown> | null;
}
export interface AuditResponse {
  entries: AuditEntry[];
  total: number;
}

export interface ReviewDecision {
  decision: 'approve' | 'override' | 'escalate';
  reviewer_role: 'counsellor' | 'regulator' | 'school_admin';
  comment: string;
}

// ---- additions (v0.2) ----
export type UiLang = 'en' | 'ar'; // 'az' optional, added last
export interface SourcesQuery {
  layer?: KBLayer;
  status?: LegalStatus;
  language?: Lang;
}
export interface AuditQuery {
  agent?: AgentId;
  run_id?: string;
  kind?: AuditEntry['kind'];
  node?: PipelineNode;
  requires_human?: boolean;
  outcome?: string;
  limit?: number;
}
export interface StartScenarioResponse {
  run_id: string;
  scenario: ScenarioSummary;
  stream_url: string;
}
export interface NextEventResponse {
  run_id: string;
  released: ScenarioEvent | null;
  remaining: number;
}
export interface ReviewDecisionResponse {
  review_id: string;
  decision: ReviewDecision['decision'];
  audit_id: string;
}
export interface AgentAssessment {
  agent: AgentId;
  summary: string;
  recommendation: string;
  confidence: number;
  citations: Citation[];
  pipeline_nodes: PipelineNode[];
  readiness_dimensions: ReadinessDimension[];
  requires_human_decision: boolean;
  audit_id: string;
}
export interface Conflict {
  agents: AgentId[];
  topic: string;
  description: string;
}

// ---- scenario room (offline rules engine) ----
export type ScenarioAgent = 'data_protection' | 'education' | 'consumer_protection' | 'ai_ethics';
export interface AgentAssessmentEvent {
  agent: ScenarioAgent;
  event_id: string;
  summary: string;
  recommendation: string;
  stance: string;
  confidence: number;
  no_source: boolean;
  matched_entry: string | null;
  citations: (GapCitation & { id: string })[];
  pipeline_nodes: PipelineNode[];
  readiness_dimensions: ReadinessDimension[];
  requires_human_decision: boolean;
  audit_id: string;
}
export interface CoordinatorEvent {
  event_id: string;
  recommendation: string;
  actions: string[];
  conflicts: Conflict[];
  expected_handling: string[];
  requires_human_decision: boolean;
  review_id: string | null;
  audit_id: string;
}

// ---- kb/data entries ----
export interface DataEntrySummary {
  id: string;
  topic: string;
  question: string;
  status: string;
  last_checked: string | null;
  layers: KBLayer[];
  citations: number;
  verified_citations: number;
  file: string;
}
export interface DataEntriesResponse {
  entries: DataEntrySummary[];
  errors: string[];
}
export interface DataEntryDetail {
  id: string;
  topic: string;
  question: string;
  answer: string;
  keywords: { en: string[]; ar: string[]; az: string[] };
  citations: GapCitation[];
  pipeline_nodes: PipelineNode[];
  readiness_dimensions: ReadinessDimension[];
  requires_human_decision: boolean;
  status: string;
  last_checked: string | null;
  file: string;
}
