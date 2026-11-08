import { Languages, Moon, Sun } from 'lucide-react';
import { useT } from '../../i18n';
import { useUi } from '../../stores/ui';

const btn =
  'pill inline-flex h-9 min-w-9 items-center justify-center gap-1.5 border border-line px-2.5 text-sm text-mut hover:text-tx hover:border-line-strong transition-colors';

export function ThemeToggle() {
  const t = useT();
  const { theme, toggleTheme } = useUi();
  const label = theme === 'dark' ? t('theme.toLight') : t('theme.toDark');
  return (
    <button type="button" onClick={toggleTheme} className={btn} aria-label={label} title={label}>
      {theme === 'dark' ? <Sun size={16} aria-hidden /> : <Moon size={16} aria-hidden />}
    </button>
  );
}

export function LangToggle() {
  const t = useT();
  const { lang, toggleLang } = useUi();
  return (
    <button type="button" onClick={toggleLang} className={btn} aria-label={t('lang.switchLabel')}>
      <Languages size={16} aria-hidden />
      <span className="hidden sm:inline">{t('lang.switchTo')}</span>
      <span aria-hidden className="sm:hidden">
        {lang === 'en' ? 'ع' : 'EN'}
      </span>
    </button>
  );
}
