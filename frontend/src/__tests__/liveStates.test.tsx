import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { AnswerView } from '../components/answer/AnswerView';
import { mockAnswer } from '../lib/mock/fixtures';
import type { ApiClient } from '../lib/client';

const h = vi.hoisted(() => ({ client: null as unknown as ApiClient }));
vi.mock('../lib/api', () => ({
  get api() {
    return h.client;
  },
  MOCK: false,
}));

async function setClient(overrides: Partial<ApiClient>) {
  const { mockClient } = await import('../lib/mock/client');
  h.client = { ...mockClient, ...overrides } as ApiClient;
}

async function renderPage() {
  const { SearchPage } = await import('../pages/SearchPage');
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <SearchPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function ask(text: string) {
  await userEvent.type(screen.getByLabelText('Your legal question'), text);
  await userEvent.click(screen.getByRole('button', { name: /^Ask/ }));
}

test('backend unreachable: health banner and ask both show the start command', async () => {
  const { ApiFailure } = await import('../lib/http/client');
  const down = new ApiFailure(0, {
    code: 'network',
    message: 'Backend unreachable at http://localhost:8000',
  });
  await setClient({
    health: () => Promise.reject(down),
    // eslint-disable-next-line require-yield
    askStream: async function* () {
      throw down;
    },
  });
  await renderPage();
  expect(await screen.findByRole('heading', { name: 'Backend not reachable' })).toBeInTheDocument();
  await ask('What consent is required?');
  const cards = await screen.findAllByRole('alert');
  expect(cards.length).toBe(2);
  expect(within(cards[1]!).getByText('.\\scripts\\start-backend.ps1')).toBeInTheDocument();
});

test('missing API key shows the configuration steps', async () => {
  const { mockHealth } = await import('../lib/mock/fixtures');
  await setClient({
    health: async () => ({ ...mockHealth, llm_configured: false, status: 'degraded' }),
  });
  await renderPage();
  expect(
    await screen.findByRole('heading', { name: 'AI model not configured' }),
  ).toBeInTheDocument();
});

test('general mode is labelled, has no citations and no Verified badge', async () => {
  await setClient({});
  await renderPage();
  await userEvent.click(screen.getByLabelText(/General AI answer/));
  expect(screen.getByText('Not from the knowledge base, not a legal source')).toBeInTheDocument();
  await ask('Explain dyslexia briefly');
  const card = await screen.findByRole('article', { name: 'General answer' }, { timeout: 4000 });
  expect(
    within(card).getByText(/not from the knowledge base, not a legal source/),
  ).toBeInTheDocument();
  expect(screen.queryByText('Legal basis')).not.toBeInTheDocument();
  expect(screen.queryByText('Verified')).not.toBeInTheDocument();
});

test('Verified badge only when verification.passed is true', async () => {
  const failed = { ...mockAnswer, verification: { ...mockAnswer.verification!, passed: false } };
  const { rerender } = render(<AnswerView result={failed} onOpenCitation={() => {}} />);
  expect(screen.queryByText('Verified')).not.toBeInTheDocument();
  expect(screen.getByText('Citations not fully verified')).toBeInTheDocument();
  rerender(<AnswerView result={mockAnswer} onOpenCitation={() => {}} />);
  expect(screen.getAllByText('Verified')).toHaveLength(2);
});
