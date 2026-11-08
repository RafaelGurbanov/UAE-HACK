import { mockClient } from '../lib/mock/client';
import type { AskStreamEvent, StreamEnvelope } from '../lib/types';

async function collect(q: string) {
  const out: AskStreamEvent[] = [];
  for await (const e of mockClient.askStream({ question: q })) out.push(e);
  return out;
}

test('answer stream ends with a final answered response and logs to audit', async () => {
  const events = await collect("What consent is required to process a child's personal data?");
  const final = events.at(-1)!;
  expect(final.type).toBe('final');
  if (final.type === 'final') {
    expect(final.data.outcome).toBe('answered');
    expect(
      final.data.answer!.legal_basis.every((c) => c.title.includes('source to be verified')),
    ).toBe(true);
  }
  expect((await mockClient.audit({ kind: 'ask' })).total).toBeGreaterThan(0);
});

test('out-of-scope question is refused with no_source', async () => {
  const final = (await collect('What is the speed limit on the highway?')).at(-1)!;
  expect(final.type === 'final' && final.data.outcome).toBe('no_source');
});

test('scenario replay releases events in order to subscribers', async () => {
  const { run_id } = await mockClient.startScenario('inapp_purchases_escalation');
  const seen: StreamEnvelope[] = [];
  mockClient.subscribeScenario('inapp_purchases_escalation', run_id, (e) => seen.push(e));
  const r1 = await mockClient.nextEvent('inapp_purchases_escalation', run_id);
  expect(r1.released?.id).toBe('e1_rollout');
  expect(r1.remaining).toBe(3);
  expect(seen.map((e) => e.type)).toContain('event_released');
  expect(seen.map((e) => e.seq)).toEqual([...seen.map((e) => e.seq)].sort((a, b) => a - b));
});
