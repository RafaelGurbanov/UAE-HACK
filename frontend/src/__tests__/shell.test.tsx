import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from '../App';
import { useUi } from '../stores/ui';

const renderAt = (path = '/') =>
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );

beforeEach(() => act(() => useUi.getState().setLang('en')));

test('top navigation lists every page', () => {
  renderAt();
  for (const name of [
    'Legal search',
    'Laws',
    'Scenario room',
    'Gap board',
    'Audit trail',
    'About',
  ]) {
    expect(screen.getAllByRole('link', { name: new RegExp(name) }).length).toBeGreaterThan(0);
  }
  expect(
    screen.getByRole('heading', { level: 1, name: 'Ask the law. See the source.' }),
  ).toBeInTheDocument();
});

test('language toggle switches to Arabic and RTL', async () => {
  renderAt();
  await userEvent.click(screen.getByRole('button', { name: /Arabic/ }));
  expect(document.documentElement.dir).toBe('rtl');
  expect(
    screen.getByRole('heading', { level: 1, name: 'اسأل القانون. شاهد المصدر.' }),
  ).toBeInTheDocument();
});

test('theme toggle flips data-theme', async () => {
  renderAt();
  const before = document.documentElement.dataset.theme;
  await userEvent.click(screen.getByRole('button', { name: /theme/ }));
  expect(document.documentElement.dataset.theme).not.toBe(before);
});

test('unknown route shows not-found page', () => {
  renderAt('/nope');
  expect(screen.getByRole('heading', { name: 'Page not found' })).toBeInTheDocument();
});
