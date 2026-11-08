// MOCK FIXTURES. Every legal reference is a labelled DEMO PLACEHOLDER, not real law:
// no real titles, law numbers, article numbers, dates, quotes or URLs. Synthetic data only.
import type {
  AskResponse,
  AuditResponse,
  Citation,
  GapsResponse,
  Health,
  LawDetail,
  ScenarioEvent,
  ScenarioSummary,
  SourceDocument,
  SourcesResponse,
  Taxonomy,
} from '../types';

export const PLACEHOLDER = 'Demo placeholder, source to be verified';

const doc = (
  id: string,
  title: string,
  layer: SourceDocument['layer'],
  domains: string[],
  lang: 'en' | 'ar' = 'en',
): SourceDocument => ({
  doc_id: id,
  title: `${title} (${PLACEHOLDER})`,
  title_ar: null,
  issuing_body: 'Demo issuing body',
  law_number: null,
  year: null,
  status: layer === 'global_example' ? 'not_legislation' : 'in_force',
  layer,
  language: lang,
  translation_of: null,
  amends: [],
  amended_by: [],
  domains,
  url: '',
  retrieved_at: null,
  verified: false,
  chunk_count: 3,
});

export const demoDocs: SourceDocument[] = [
  doc('demo-uae-data', 'Demo federal data protection law', 'uae_federal', [
    'children_data',
    'consent',
    'cross_border_transfer',
  ]),
  doc('demo-uae-child', 'Demo federal child protection law', 'uae_federal', [
    'children_data',
    'education',
  ]),
  doc('demo-uae-consumer', 'Demo federal consumer protection law', 'uae_federal', [
    'in_app_purchases',
    'advertising_minors',
  ]),
  doc('demo-emirate-school', 'Demo emirate inclusive education policy', 'emirate', [
    'education',
    'disability_inclusion',
  ]),
  doc('demo-global-ads', 'Demo global example on ads to minors', 'global_example', [
    'advertising_minors',
  ]),
];

const cite = (id: string, d: SourceDocument, article: string, score: number): Citation => ({
  id,
  chunk_id: `${d.doc_id}:art-${article}`,
  doc_id: d.doc_id,
  title: d.title,
  law_number: null,
  year: null,
  article,
  clause: null,
  quote: `${PLACEHOLDER}: illustrative clause text for article ${article}.`,
  url: '',
  layer: d.layer,
  status: d.status,
  language: d.language,
  score,
  verified: true,
});

export const mockHealth: Health = {
  status: 'ok',
  version: '0.2.0-mock',
  llm_provider: 'mock',
  llm_model: 'mock-1',
  llm_configured: true,
  embedding_provider: 'mock',
  embedding_model: 'mock',
  kb_documents: demoDocs.length,
  kb_chunks: demoDocs.length * 3,
  index_chunks: demoDocs.length * 3,
  audit_entries: 0,
  problems: [],
  answer_mode: 'llm',
  data_entries: 0,
  data_errors: [],
  semantic_search: false,
};

export const mockTaxonomy: Taxonomy = {
  pipeline_nodes: [
    { id: 'SRC', label: 'Smart pen & writing board' },
    { id: 'C', label: 'School edge compute platform' },
    { id: 'PP', label: 'Pre-processing / harmonisation' },
    { id: 'M', label: 'Models (anomaly detection, handwriting analysis)' },
    { id: 'P', label: 'Policy & human review (counsellor)' },
    { id: 'D', label: 'Provider cloud analytics platform' },
    { id: 'SINK', label: 'Parent / teacher mobile app' },
  ],
  readiness_dimensions: [
    { id: 'open_data_open_source', label: 'Open data and open-source management' },
    { id: 'generative_ai_content_ecosystem', label: 'Generative AI content ecosystem' },
    {
      id: 'contextualisation_regional_development',
      label: 'Contextualisation and regional development',
    },
    {
      id: 'domain_integration_cross_domain',
      label: 'AI integration in domains and cross-domain analysis',
    },
    { id: 'human_interaction_supervision', label: 'Human interaction and supervision' },
    { id: 'ai_policy_implementation', label: 'AI policy and implementation opportunities' },
    { id: 'ai_social_inclusion', label: 'AI for social inclusion' },
    { id: 'digital_infrastructure_energy', label: 'Digital infrastructure and energy' },
  ],
  layers: ['uae_federal', 'emirate', 'global_example'],
  gap_types: [
    'unclear_responsibility',
    'missing_standard',
    'legislative_gap',
    'coordination_problem',
    'objective_conflict',
  ],
  domains: [
    'children_data',
    'consent',
    'education',
    'in_app_purchases',
    'advertising_minors',
    'cross_border_transfer',
    'automated_decisions',
    'disability_inclusion',
    'cybersecurity',
    'ai_ethics',
  ],
  agents: [
    'legal_adviser',
    'data_protection',
    'education',
    'consumer_protection',
    'ai_ethics',
    'coordinator',
    'gap_analyst',
  ],
};

export const mockSources: SourcesResponse = {
  documents: demoDocs,
  coverage: demoDocs.flatMap((d) =>
    d.domains.map((domain) => ({ layer: d.layer, domain, documents: 1 })),
  ),
  total_documents: demoDocs.length,
  total_chunks: demoDocs.length * 3,
};

export const mockLaws: Record<string, LawDetail> = Object.fromEntries(
  demoDocs.map((d) => [
    d.doc_id,
    {
      document: d,
      translations: [],
      articles: ['demo-1', 'demo-2', 'demo-3'].map((a) => ({
        article: a,
        heading: `Demo heading ${a}`,
        chapter: 'Demo chapter',
        text: `${PLACEHOLDER}: illustrative clause text for article ${a}. This article text is illustrative only and will be replaced by verified text from the knowledge base.`,
        chunk_ids: [`${d.doc_id}:art-${a}`],
        amended: false,
      })),
    },
  ]),
);

const [dData, dChild] = demoDocs as [SourceDocument, SourceDocument, ...SourceDocument[]];

export const mockAnswer: AskResponse = {
  answer_id: 'ans_mock_1',
  conversation_id: 'conv_mock',
  outcome: 'answered',
  mode: 'grounded',
  language: 'en',
  answer: {
    short_answer: `In this demo, processing a child's personal data requires consent from a parent or guardian [c1], and screening flags must be reviewed by a counsellor before results are shared [c2]. (${PLACEHOLDER}.)`,
    legal_basis: [cite('c1', dData, 'demo-1', 0.84), cite('c2', dChild, 'demo-2', 0.77)],
    details:
      'Demo detail: conditions and exceptions appear here only when present in retrieved text.',
    status_and_limits: 'Demo mode: no real sources were searched. Status shown is illustrative.',
    related: ['Purpose limitation (demo)', 'Data retention (demo)'],
    disclaimer: 'Informational only, not legal advice. The official Arabic text prevails.',
  },
  no_source_message: null,
  suggested_topics: [],
  pipeline_nodes: ['SRC', 'PP', 'P'],
  readiness_dimensions: ['human_interaction_supervision', 'ai_social_inclusion'],
  verification: { passed: true, checked: 2, verified: 2, removed: [], warnings: [] },
  requires_human_decision: true,
  audit_id: 'aud_mock_pending',
};

export const mockNoSource: AskResponse = {
  answer_id: 'ans_mock_2',
  conversation_id: 'conv_mock',
  outcome: 'no_source',
  mode: 'grounded',
  language: 'en',
  answer: null,
  no_source_message: 'No supporting source found in the knowledge base',
  suggested_topics: ["Children's data", 'Consent', 'Cross-border transfer'],
  pipeline_nodes: [],
  readiness_dimensions: [],
  verification: null,
  requires_human_decision: false,
  audit_id: 'aud_mock_pending',
};

export const mockGeneral: AskResponse = {
  answer_id: 'ans_mock_3',
  conversation_id: 'conv_mock',
  outcome: 'general',
  mode: 'general',
  language: 'en',
  answer: {
    short_answer:
      'Demo general answer: in mock mode no AI model is called. In live mode this text comes from the LLM without retrieval.',
    legal_basis: [],
    details: null,
    status_and_limits: 'Not from the knowledge base, not a legal source.',
    related: [],
    disclaimer: 'Informational only, not legal advice. The official Arabic text prevails.',
  },
  no_source_message: null,
  suggested_topics: [],
  pipeline_nodes: [],
  readiness_dimensions: [],
  verification: null,
  requires_human_decision: false,
  audit_id: 'aud_mock_pending',
};

export const mockScenarios: ScenarioSummary[] = [
  {
    id: 'inapp_purchases_escalation',
    title: 'National rollout to inferred-disability ad targeting',
    description: 'Consumer protection issue escalates into a children’s-data and AI-ethics breach.',
    controversial: false,
    total_events: 4,
  },
  {
    id: 'false_positive_controversy',
    title: 'False-positive flag, parental refusal and cloud transfer abroad',
    description: 'The screening itself becomes controversial.',
    controversial: true,
    total_events: 3,
  },
];

export const mockScenarioEvents: Record<string, ScenarioEvent[]> = {
  inapp_purchases_escalation: [
    {
      id: 'e1_rollout',
      step: 1,
      at: 'T+0',
      title: 'National deployment',
      description:
        'The smart classroom solution is deployed nationally and becomes popular with students.',
      severity: 'info',
      visible_to: [
        'education',
        'data_protection',
        'consumer_protection',
        'ai_ethics',
        'coordinator',
      ],
      pipeline_nodes: ['SRC', 'C', 'PP', 'M', 'P', 'D', 'SINK'],
    },
    {
      id: 'e2_iap',
      step: 2,
      at: 'T+6 months',
      title: 'In-app purchases promoted to students',
      description:
        'The education department notices the provider promoting in-app purchases; students spend significant money.',
      severity: 'warning',
      visible_to: ['education', 'consumer_protection', 'coordinator'],
      pipeline_nodes: ['SINK', 'D'],
    },
    {
      id: 'e3_monitoring',
      step: 3,
      at: 'T+6.5 months',
      title: 'Monitoring under agreed rules',
      description:
        'Agencies monitor and discuss actions strictly under pre-agreed knowledge-base policies.',
      severity: 'warning',
      visible_to: ['education', 'consumer_protection', 'data_protection', 'coordinator'],
      pipeline_nodes: ['P', 'D', 'SINK'],
    },
    {
      id: 'e4_inferred_ads',
      step: 4,
      at: 'T+7 months',
      title: 'Targeted ads from inferred disability signals',
      description:
        'Monitoring agencies observe ads targeted using inferred dyslexia/dysgraphia signals.',
      severity: 'critical',
      visible_to: ['data_protection', 'ai_ethics', 'consumer_protection', 'coordinator'],
      pipeline_nodes: ['M', 'D', 'SINK'],
    },
  ],
  false_positive_controversy: [
    {
      id: 'c1_false_positive',
      step: 1,
      at: 'T+0',
      title: 'False-positive flag',
      description:
        'A synthetic student is flagged; the counsellor finds no difficulty, but a teacher already saw the flag.',
      severity: 'warning',
      visible_to: ['education', 'ai_ethics', 'coordinator'],
      pipeline_nodes: ['M', 'P', 'SINK'],
    },
    {
      id: 'c2_parental_refusal',
      step: 2,
      at: 'T+2 weeks',
      title: 'Parents refuse consent',
      description: 'Several parents refuse consent and ask for existing data to be deleted.',
      severity: 'warning',
      visible_to: ['data_protection', 'education', 'coordinator'],
      pipeline_nodes: ['SRC', 'D'],
    },
    {
      id: 'c3_cross_border',
      step: 3,
      at: 'T+1 month',
      title: 'Cloud processing abroad',
      description: 'The provider moves analytics to a data centre outside the UAE.',
      severity: 'critical',
      visible_to: ['data_protection', 'coordinator'],
      pipeline_nodes: ['D'],
    },
  ],
};

export const mockGaps: GapsResponse = { gaps: [], readiness_radar: {} };
export const mockAudit: AuditResponse = { entries: [], total: 0 };
