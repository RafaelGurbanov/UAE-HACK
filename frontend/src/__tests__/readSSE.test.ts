import { readSSE } from '../lib/http/client';

function resp(chunks: string[]) {
  const enc = new TextEncoder();
  return new Response(
    new ReadableStream({
      start(c) {
        chunks.forEach((x) => c.enqueue(enc.encode(x)));
        c.close();
      },
    }),
  );
}

test('parses CRLF events split across chunks, skips pings, flushes the last block', async () => {
  const r = resp([
    'event: retrieval\r\ndata: {"a":',
    '1}\r\n\r\n: ping\r\n\r\nevent: token\r\ndata: {"text":"hi"}\r\n\r\nevent: final\r\ndata: {}',
  ]);
  const out = [];
  for await (const m of readSSE(r)) out.push(m);
  expect(out).toEqual([
    { event: 'retrieval', data: '{"a":1}' },
    { event: 'token', data: '{"text":"hi"}' },
    { event: 'final', data: '{}' },
  ]);
});
