import { render, screen, within } from '@testing-library/react';
import { AnswerView, ExtractiveView, GuidanceView } from '../components/answer/AnswerView';
import { isVerified } from '../components/answer/VerifyBadge';
import type { AskResponse, Citation } from '../lib/types';

const cite = (over: Partial<Citation> = {}): Citation => ({
  id: 'c1',
  chunk_id: 'data:children-data-consent:1',
  doc_id: 'data:children-data-consent',
  title: 'SOURCE TO BE VERIFIED',
  law_number: null,
  year: null,
  article: 'SOURCE TO BE VERIFIED',
  clause: null,
  quote: 'SOURCE TO BE VERIFIED',
  url: '',
  layer: 'uae_federal',
  status: 'unknown',
  language: 'en',
  score: 1,
  verified: false,
  ...over,
});

const offline = (over: Partial<AskResponse> = {}): AskResponse => ({
  answer_id: 'a',
  conversation_id: 'c',
  outcome: 'answered',
  mode: 'offline_json',
  language: 'en',
  matched_entry: 'children-data-consent',
  answer: {
    short_answer: 'Draft guidance, to be confirmed against verified UAE sources: obtain consent.',
    legal_basis: [cite()],
    details: null,
    status_and_limits: 'Answered from knowledge base data (no AI generation).',
    related: [],
    disclaimer: 'Informational only.',
  },
  no_source_message: null,
  suggested_topics: [],
  pipeline_nodes: ['SRC'],
  readiness_dimensions: [],
  verification: { passed: false, checked: 1, verified: 0, removed: [], warnings: [] },
  requires_human_decision: true,
  audit_id: 'x',
  ...over,
});

test('offline entry shows the no-AI label and never "Verified" for verified=false', () => {
  render(<AnswerView result={offline()} onOpenCitation={() => {}} />);
  expect(
    screen.getByText('Answered from knowledge base data (no AI generation)'),
  ).toBeInTheDocument();
  expect(screen.getByText('Source to be verified')).toBeInTheDocument();
  expect(screen.queryByText('Verified')).not.toBeInTheDocument();
  expect(screen.queryByText('Citations not fully verified')).not.toBeInTheDocument(); // LLM-only banner
});

test('offline citation with verified=true shows Verified (per citation, not per answer)', () => {
  const r = offline({
    answer: { ...offline().answer!, legal_basis: [cite(), cite({ id: 'c2', verified: true })] },
  });
  render(<AnswerView result={r} onOpenCitation={() => {}} />);
  expect(screen.getAllByText('Verified')).toHaveLength(1);
  expect(screen.getAllByText('Source to be verified')).toHaveLength(1);
});

test('badge rule: offline uses the citation flag; LLM needs verification.passed too', () => {
  expect(isVerified(offline(), cite({ verified: true }))).toBe(true);
  expect(isVerified(offline(), cite({ verified: false }))).toBe(false);
  const llm = offline({
    mode: 'grounded',
    verification: { passed: false, checked: 1, verified: 1, removed: [], warnings: [] },
  });
  expect(isVerified(llm, cite({ verified: true }))).toBe(false);
});

test('extractive passages are labelled and shown verbatim', () => {
  const r = offline({
    mode: 'extractive',
    matched_entry: null,
    answer: {
      ...offline().answer!,
      short_answer: 'Passage from source document: 1 matching passage(s)',
      legal_basis: [
        cite({
          id: 'p1',
          chunk_id: 'demo-act:art-5',
          doc_id: 'demo-act',
          title: 'demo act',
          article: '5',
          quote:
            'Whoever violates Article 2 or Article 3 shall be liable to an administrative fine.',
        }),
      ],
    },
  });
  render(<ExtractiveView result={r} onOpenCitation={() => {}} />);
  const item = screen.getByRole('listitem');
  expect(within(item).getByText('Passage from source document')).toBeInTheDocument();
  expect(within(item).getByText(/shall be liable to an administrative fine/)).toBeInTheDocument();
  expect(within(item).getByText('Source to be verified')).toBeInTheDocument();
});

test('guidance renders as a how-to message, not an answer', () => {
  const r = offline({
    outcome: 'guidance',
    mode: 'guidance',
    answer: {
      ...offline().answer!,
      short_answer: 'Hello! I answer questions about UAE rules.',
      legal_basis: [],
    },
  });
  render(<GuidanceView result={r} />);
  expect(screen.getByRole('heading', { name: 'How to ask' })).toBeInTheDocument();
  expect(screen.queryByText('Legal basis')).not.toBeInTheDocument();
});
