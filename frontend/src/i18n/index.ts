import { useCallback } from 'react';
import { useUi } from '../stores/ui';
import { ar } from './ar';
import { en, type MessageKey } from './en';

const dictionaries = { en, ar } as const;

export function translate(
  lang: keyof typeof dictionaries,
  key: MessageKey,
  vars?: Record<string, string | number>,
) {
  let s: string = dictionaries[lang][key] ?? en[key];
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.replace(`{${k}}`, String(v));
  return s;
}

export function useT() {
  const lang = useUi((s) => s.lang);
  return useCallback(
    (key: MessageKey, vars?: Record<string, string | number>) => translate(lang, key, vars),
    [lang],
  );
}

export type { MessageKey };
