import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PipelineMap } from '../components/pipeline/PipelineMap';

test('renders all seven Y.3172 nodes and lights only the active ones', () => {
  render(<PipelineMap active={['M', 'D']} />);
  const buttons = screen.getAllByRole('button');
  expect(buttons.map((b) => b.textContent)).toEqual(['SRC', 'C', 'PP', 'M', 'P', 'D', 'SINK']);
  const lit = buttons.filter((b) => b.hasAttribute('data-active')).map((b) => b.textContent);
  expect(lit).toEqual(['M', 'D']);
  expect(screen.getByRole('button', { name: /^M: .*Touched/ })).toBeInTheDocument();
});

test('selecting a node shows what it covers', async () => {
  render(<PipelineMap active={[]} />);
  await userEvent.click(screen.getByRole('button', { name: /^P:/ }));
  expect(screen.getByText(/Counsellor review/, { selector: 'span' })).toBeInTheDocument();
  expect(screen.getByText(/Human interaction and supervision/)).toBeInTheDocument();
});
