import { AnimatePresence, motion } from 'framer-motion';
import { Link, useLocation, useOutlet } from 'react-router-dom';
import { useT } from '../../i18n';
import { SECONDARY_ITEMS } from './navItems';
import { TopNav } from './TopNav';

export function AppShell() {
  const t = useT();
  const location = useLocation();
  const outlet = useOutlet();
  return (
    <div className="aurora flex min-h-dvh flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:start-3 focus:top-3 focus:z-50 focus:rounded-md focus:bg-bg2 focus:px-3 focus:py-2"
      >
        {t('app.skip')}
      </a>
      <TopNav />
      <main
        id="main"
        tabIndex={-1}
        className="mx-auto w-full max-w-[1080px] flex-1 px-4 py-8 outline-none sm:px-6 sm:py-12"
      >
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.22, ease: 'easeOut' }}
          >
            {outlet}
          </motion.div>
        </AnimatePresence>
      </main>
      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-[1080px] flex-col items-center gap-3 px-4 py-5 text-xs text-mut sm:flex-row sm:justify-between sm:px-6">
          <p>{t('app.disclaimer')}</p>
          <nav aria-label={t('nav.secondary')}>
            <ul className="flex gap-4">
              {SECONDARY_ITEMS.map(({ to, key }) => (
                <li key={to}>
                  <Link to={to} className="underline-offset-4 hover:text-tx hover:underline">
                    {t(key)}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </footer>
    </div>
  );
}
