import { useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { useT } from '../../i18n';

/** A copyable shell command. Clipboard is optional (may be refused in some frames). */
export function Command({ cmd }: { cmd: string }) {
  const t = useT();
  const [done, setDone] = useState(false);
  return (
    <div
      dir="ltr"
      className="flex items-center gap-2 rounded-xl border border-line bg-bg2 px-3 py-2 text-start"
    >
      <code className="min-w-0 flex-1 overflow-x-auto whitespace-pre font-mono text-xs text-tx">
        {cmd}
      </code>
      <button
        type="button"
        aria-label={done ? t('live.copied') : t('live.copy')}
        title={done ? t('live.copied') : t('live.copy')}
        className="shrink-0 text-mut hover:text-tx"
        onClick={() => {
          navigator.clipboard?.writeText(cmd).then(
            () => {
              setDone(true);
              setTimeout(() => setDone(false), 1500);
            },
            () => {},
          );
        }}
      >
        {done ? <Check size={14} aria-hidden /> : <Copy size={14} aria-hidden />}
      </button>
    </div>
  );
}
