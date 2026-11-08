import { BookCheck, Sparkles } from 'lucide-react';
import { useId } from 'react';
import { useT } from '../../i18n';
import type { AskMode } from '../../lib/types';

export function ModeToggle({
  mode,
  onChange,
  disabled,
  generalAvailable = true,
}: {
  mode: AskMode;
  onChange: (m: AskMode) => void;
  disabled?: boolean;
  /** false in offline mode: general answers need an LLM */
  generalAvailable?: boolean;
}) {
  const t = useT();
  const name = useId();
  const opts: { value: AskMode; label: string; icon: typeof BookCheck }[] = [
    { value: 'grounded', label: t('mode.grounded'), icon: BookCheck },
    { value: 'general', label: t('mode.general'), icon: Sparkles },
  ];
  return (
    <fieldset className="mt-4 flex flex-col items-center gap-1.5" disabled={disabled}>
      <legend className="sr-only">{t('mode.label')}</legend>
      <div className="pill inline-flex border border-line bg-bg2 p-1">
        {opts.map(({ value, label, icon: Icon }) => {
          const off = value === 'general' && !generalAvailable;
          return (
            <label
              key={value}
              title={off ? t('offline.generalOff') : undefined}
              className={`pill inline-flex items-center gap-1.5 px-3 py-1.5 text-sm transition-colors has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-teal ${
                off ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'
              } ${mode === value ? 'bg-card-strong text-tx shadow-glow-teal' : 'text-mut hover:text-tx'}`}
            >
              <input
                type="radio"
                name={name}
                value={value}
                checked={mode === value}
                disabled={off}
                onChange={() => onChange(value)}
                className="sr-only"
              />
              <Icon size={14} aria-hidden /> {label}
            </label>
          );
        })}
      </div>
      {mode === 'general' && generalAvailable && (
        <p className="text-xs text-amb-ink">{t('mode.generalHint')}</p>
      )}
      {!generalAvailable && <p className="text-xs text-mut">{t('offline.generalOff')}</p>}
    </fieldset>
  );
}
