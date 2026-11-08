# Frontend: Qalam Policy Command Centre

A static React site. `VITE_MOCK=true` gives the public demo, which needs no backend. `VITE_MOCK=false` gives live mode against FastAPI, per `docs/api.md`.

## Data layer
```
src/lib/client.ts        ApiClient interface (the only thing pages depend on)
src/lib/http/client.ts   live: REST + SSE (fetch-stream for /ask, EventSource for scenarios)
src/lib/mock/client.ts   mock: fixtures, scripted SSE replay, in-memory audit log
src/lib/mock/fixtures.ts every legal reference = "Demo placeholder, source to be verified"
src/lib/api.ts           export const api = MOCK ? mockClient : httpClient
src/lib/types.ts         mirrors backend/app/api/schemas.py
```
React Query wraps `api.*` in `src/hooks/` (one hook per resource). Zustand (`src/stores/ui.ts`) holds only language and theme. Scenario run state goes in a small store in Phase 3.

## Component tree (✅ = built)
```
main.tsx: QueryClientProvider > MotionConfig(reducedMotion=user) > BrowserRouter(basename) ✅
└ App routes ✅
  └ AppShell: skip link, TopNav, animated <Outlet>, footer disclaimer ✅
     ├ TopNav: logo, DemoBadge, NavLinks, mobile menu, LangToggle, ThemeToggle ✅
     ├ /            SearchPage ✅ (Phase 2)
     │   ├ SearchHero ✅: violet-glow search bar, rotating example, topic chips, gold Ask button
     │   ├ PipelineMap ✅: 7 nodes on a line, teal pulse (RTL-aware), lit = gold border/fill/glow, node detail ★
     │   ├ AnswerView ✅ + DraftView ✅ (dimmed, unverified stream): short answer with inline [cN] chips, legal basis cards, details,
     │   │             StatusLimits, Related, NodeBadges, DimensionBadges, HumanDecisionFlag, Disclaimer
     │   ├ NoSourceNotice ✅: plain refusal + suggested topics
     │   └ CitationDrawer ✅: native <dialog> side sheet; metadata, verified quote, article text with the quote highlighted, official link or "No verified link yet", → /laws/:id#art-x
     ├ /laws         LawsPage: coverage matrix, filterable document list   (Phase 4)
     ├ /laws/:id     LawDetailPage: ArticleNav (sticky) + article list     (Phase 4)
     ├ /scenario     ScenarioPage                                  (Phase 3)
     │   ├ ScenarioPicker, EventTimeline (severity blue→amber→red), ReleaseNextButton
     │   ├ PipelineMap (shared, highlights from pipeline_highlight)
     │   ├ AgentCouncil > AgentCard×4: seen events only, status, assessment, ConfidenceRing
     │   ├ CoordinatorPanel: recommendation, ConflictList
     │   └ HumanReviewPanel: Approve / Override / Escalate + comment (logged)
     ├ /gaps         GapsPage: GapTypeFilter, GapCard (UAE says | Global example says | Gap, analysis not law), ReadinessRadar (Recharts)   (Phase 4)
     ├ /audit        AuditPage: AuditFilters (agent/node/result), AuditTerminal (mono rows, expandable reasoning + chunks), Copy JSON, Download JSON   (Phase 4)
     └ /about        AboutPage: how it works, Y.3172 table, readiness dimensions, limits, legal notice   (Phase 4)
Shared: PageHeader ✅, Skeleton/LoadingBlock ✅, EmptyState ✅, ErrorState ✅, NodeBadges ✅, DimensionBadges ✅, LayerPill ✅, RequiresDecision ✅, SeverityPill
Hooks: useAskStream ✅ (abortable stream state machine), useLaw ✅ (React Query)
```

## Design tokens
`src/styles/tokens.css` holds CSS variables for each theme (`[data-theme=dark|light]`). `index.css` maps them to Tailwind utilities (`bg-surface`, `text-muted`, `border-line`, `text-teal`, `shadow-glow-active`, `text-sev-critical`, …). The values come from `docs/prototype/tokens.md`, plus derived AA-safe `*-ink` text variants for the light theme. Components use only the token utilities, so swapping values changes nothing else.

## Conventions
- API-provided text gets `dir="auto"`, so English legal text stays LTR inside the Arabic UI and vice versa.
- Sentence case, no all-caps eyebrows, no decorative numbering.
- Fonts: Fraunces for headings, Instrument Sans for body, JetBrains Mono for logs only. Self-hosted via Fontsource (no third-party font requests).
- Logical CSS properties only (`ms-`, `me-`, `start-`, `text-start`), so RTL works without overrides.
- All strings go through `useT()`. `en.ts` defines the keys, and `ar.ts` must match them (enforced by the type checker).
- Motion: Framer Motion with `reducedMotion="user"`. The CSS reduced-motion guard covers everything else.
- Deploy: `VITE_BASE` sets the base path. SPA fallback via `public/_redirects` (Netlify), `vercel.json`, and `dist/404.html` (GitHub Pages).
