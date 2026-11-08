import { SearchX } from 'lucide-react';
import { useT } from '../../i18n';
import type { AskResponse } from '../../lib/types';

export function NoSourceNotice({
  result,
  onTopic,
}: {
  result: AskResponse;
  onTopic: (q: string) => void;
}) {
  const t = useT();
  return (
    <article role="status" className="card p-5 sm:p-7">
      <div className="flex items-start gap-3">
        <SearchX className="mt-1 shrink-0 text-mut" aria-hidden />
        <div>
          <h2 className="text-xl">{t('refusal.title')}</h2>
          <p className="mt-2 text-mut">{t('refusal.body')}</p>
        </div>
      </div>
      {result.suggested_topics.length > 0 && (
        <ul className="mt-5 flex flex-wrap gap-2">
          {result.suggested_topics.map((topic) => (
            <li key={topic}>
              <button type="button" className="btn-ghost text-sm" onClick={() => onTopic(topic)}>
                {topic}
              </button>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}
