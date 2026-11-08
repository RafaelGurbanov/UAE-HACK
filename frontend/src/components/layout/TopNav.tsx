import { useEffect, useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { Menu, PenLine, X } from 'lucide-react';
import { useT } from '../../i18n';
import { DemoBadge } from './DemoBadge';
import { NAV_ITEMS, SECONDARY_ITEMS } from './navItems';
import { LangToggle, ThemeToggle } from './Toggles';

const linkCls = ({ isActive }: { isActive: boolean }) =>
  `pill flex items-center gap-2 whitespace-nowrap px-3 py-1.5 text-sm transition-colors ${
    isActive ? 'bg-card-strong text-tx shadow-glow-teal' : 'text-mut hover:text-tx'
  }`;

export function TopNav() {
  const t = useT();
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  useEffect(() => setOpen(false), [pathname]);

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-[var(--nav-bg)] backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[1080px] items-center gap-2 px-4 sm:gap-3 sm:px-6">
        <Link
          to="/"
          className="flex shrink-0 items-center gap-2 whitespace-nowrap font-display text-lg font-bold text-tx"
        >
          <PenLine size={20} className="text-teal" aria-hidden />
          <span>{t('app.short')}</span>
        </Link>
        <DemoBadge />
        <nav aria-label={t('nav.main')} className="ms-auto hidden md:block">
          <ul className="flex items-center gap-1">
            {NAV_ITEMS.map(({ to, key, icon: Icon }) => (
              <li key={to}>
                <NavLink to={to} end={to === '/'} className={linkCls}>
                  <Icon size={15} aria-hidden /> {t(key)}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <div className="ms-auto flex shrink-0 items-center gap-1.5 sm:gap-2 md:ms-2">
          <LangToggle />
          <ThemeToggle />
          <button
            type="button"
            className="pill inline-flex h-9 w-9 items-center justify-center border border-line text-mut hover:text-tx md:hidden"
            aria-expanded={open}
            aria-controls="mobile-nav"
            aria-label={t('nav.menu')}
            onClick={() => setOpen((o) => !o)}
          >
            {open ? <X size={18} aria-hidden /> : <Menu size={18} aria-hidden />}
          </button>
        </div>
      </div>
      {open && (
        <nav
          id="mobile-nav"
          aria-label={t('nav.main')}
          className="border-t border-line px-4 pb-4 md:hidden"
        >
          <ul className="mt-3 grid gap-1">
            {[...NAV_ITEMS, ...SECONDARY_ITEMS].map(({ to, key, icon: Icon }) => (
              <li key={to}>
                <NavLink to={to} end={to === '/'} className={linkCls}>
                  <Icon size={15} aria-hidden /> {t(key)}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      )}
    </header>
  );
}
