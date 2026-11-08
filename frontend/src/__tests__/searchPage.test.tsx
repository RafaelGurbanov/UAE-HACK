import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { SearchPage } from '../pages/SearchPage';

vi.mock('../lib/api', async () => {
  const { mockClient } = await import('../lib/mock/client');
  return { api: mockClient, MOCK: true };
});

function renderPage() {
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

test('answered question shows the six-part answer, lights the pipeline and opens the citation drawer', async () => {
  renderPage();
  await ask("What consent is required to process a child's data?");

  const answer = await screen.findByRole('article', { name: 'Short answer' }, { timeout: 5000 });
  expect(within(answer).getByText('Legal basis')).toBeInTheDocument();
  expect(within(answer).getByText('Status and limits')).toBeInTheDocument();
  expect(within(answer).getByText('Requires counsellor or regulator decision')).toBeInTheDocument();
  expect(within(answer).getAllByText(/source to be verified/).length).toBeGreaterThan(0);

  const lit = screen
    .getAllByRole('button')
    .filter((b) => b.hasAttribute('data-active'))
    .map((b) => b.textContent);
  expect(lit).toEqual(['SRC', 'PP', 'P']);

  await userEvent.click(
    within(answer).getByRole('button', { name: 'Open source for citation c1' }),
  );
  const drawer = await screen.findByRole('dialog', { name: 'Source' });
  expect(await within(drawer).findByText(/illustrative only/)).toBeInTheDocument();
  expect(within(drawer).getByRole('link', { name: 'View full law' })).toHaveAttribute(
    'href',
    '/laws/demo-uae-data#art-demo-1',
  );
  expect(within(drawer).getByText('No verified link yet')).toBeInTheDocument();
}, 10000);

test('out-of-scope question shows the plain refusal with suggested topics', async () => {
  renderPage();
  await ask('What is the speed limit on the highway?');
  const heading = await screen.findByRole(
    'heading',
    { name: 'No supporting source found in the knowledge base' },
    { timeout: 4000 },
  );
  const notice = heading.closest('article')!;
  expect(within(notice).getByRole('button', { name: 'Cross-border transfer' })).toBeInTheDocument();
  expect(screen.queryByText('Legal basis')).not.toBeInTheDocument();
});
