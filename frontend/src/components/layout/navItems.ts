import {
  Activity,
  BookOpen,
  GitCompareArrows,
  Info,
  ScrollText,
  Search,
  type LucideIcon,
} from 'lucide-react';
import type { MessageKey } from '../../i18n';

export interface NavItem {
  to: string;
  key: MessageKey;
  icon: LucideIcon;
}

/** Primary nav, as specified in docs/prototype/tokens.md */
export const NAV_ITEMS: NavItem[] = [
  { to: '/', key: 'nav.search', icon: Search },
  { to: '/scenario', key: 'nav.scenario', icon: Activity },
  { to: '/gaps', key: 'nav.gaps', icon: GitCompareArrows },
  { to: '/audit', key: 'nav.audit', icon: ScrollText },
];

/** Secondary routes, linked from the footer (and the mobile menu) */
export const SECONDARY_ITEMS: NavItem[] = [
  { to: '/laws', key: 'nav.laws', icon: BookOpen },
  { to: '/about', key: 'nav.about', icon: Info },
];
