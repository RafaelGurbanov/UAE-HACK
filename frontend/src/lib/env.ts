/**
 * Where the API lives.
 * - Dev server (`npm run dev`): same origin. Vite proxies /api to the backend (see vite.config.ts),
 *   so the browser never makes a cross-origin call. This works in locked-down browsers too.
 * - Static builds (deploy, Docker): VITE_API_URL, e.g. https://api.example.org
 */
const configured = (import.meta.env.VITE_API_URL as string | undefined) ?? '';
export const API_URL =
  import.meta.env.DEV && import.meta.env.MODE !== 'test'
    ? ''
    : configured || 'http://localhost:8000';
/** Human-readable location of the API, for messages. */
export const API_LABEL =
  API_URL || `${typeof window !== 'undefined' ? window.location.origin : ''}/api`;
export const MOCK = import.meta.env.VITE_MOCK === 'true';
