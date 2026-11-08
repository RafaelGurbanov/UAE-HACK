import type { ApiClient } from './client';
import { MOCK } from './env';
import { httpClient } from './http/client';
import { mockClient } from './mock/client';

/** Single entry point. VITE_MOCK=true -> fixtures; otherwise the FastAPI backend. */
export const api: ApiClient = MOCK ? mockClient : httpClient;
export { MOCK };
export type { ApiClient };
