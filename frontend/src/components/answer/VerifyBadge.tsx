import { BadgeCheck, CircleAlert } from 'lucide-react';
import { useT } from '../../i18n';
import { OFFLINE_MODES, type AskResponse, type Citation } from '../../lib/types';

/**
 * The single rule for the "Verified" badge.
 * - Offline modes (kb/data entry, verbatim passage): the citation's own human-set `verified` flag.
 * - LLM mode: the server-side checker must have passed the whole answer AND this citation.
 */
export function isVerified(
  result: Pick<AskResponse, 'mode' | 'verification'> | null,
  c: Citation,
): boolean {
  if (!result) return false;
  if (OFFLINE_MODES.includes(result.mode)) return c.verified === true;
  return !!result.verification?.passed && c.verified === true;
}

export function VerifyBadge({ ok, offline }: { ok: boolean; offline: boolean }) {
  const t = useT();
  return (
    <span
      className={`inline-flex items-center gap-1 text-[11px] ${ok ? 'text-teal-ink' : offline ? 'text-amb-ink' : 'text-red-ink'}`}
    >
      {ok ? <BadgeCheck size={13} aria-hidden /> : <CircleAlert size={13} aria-hidden />}
      {ok ? t('answer.verified') : offline ? t('answer.toVerify') : t('answer.unverified')}
    </span>
  );
}
