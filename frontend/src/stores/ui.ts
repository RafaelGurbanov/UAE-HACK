import { create } from 'zustand';
import type { UiLang } from '../lib/types';

export type Theme = 'dark' | 'light';
const STORAGE_KEY = 'qalam-ui';

function readSaved(): Partial<{ lang: UiLang; theme: Theme }> {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}') as Partial<{
      lang: UiLang;
      theme: Theme;
    }>;
  } catch {
    return {};
  }
}
function save(state: { lang: UiLang; theme: Theme }) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    /* storage unavailable */
  }
}

/** Dark by default; respect an explicit OS preference for light. */
function initialTheme(saved?: Theme): Theme {
  if (saved) return saved;
  return typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-color-scheme: light)').matches
    ? 'light'
    : 'dark';
}

export function applyToDocument(lang: UiLang, theme: Theme) {
  const el = document.documentElement;
  el.lang = lang;
  el.dir = lang === 'ar' ? 'rtl' : 'ltr';
  el.dataset.theme = theme;
}

interface UiState {
  lang: UiLang;
  theme: Theme;
  setLang: (l: UiLang) => void;
  toggleLang: () => void;
  toggleTheme: () => void;
}

const saved = readSaved();

export const useUi = create<UiState>((set, get) => ({
  lang: saved.lang ?? 'en',
  theme: initialTheme(saved.theme),
  setLang: (lang) => {
    set({ lang });
    applyToDocument(lang, get().theme);
    save({ lang, theme: get().theme });
  },
  toggleLang: () => get().setLang(get().lang === 'en' ? 'ar' : 'en'),
  toggleTheme: () => {
    const theme: Theme = get().theme === 'dark' ? 'light' : 'dark';
    set({ theme });
    applyToDocument(get().lang, theme);
    save({ lang: get().lang, theme });
  },
}));
