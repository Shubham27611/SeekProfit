# SeekProfit — Product Memory

## Original problem statement
Build the initial FOUNDATION of a production-quality SaaS web app called **SeekProfit** — an AI-powered financial intelligence platform for businesses. Core product promise: **"Find the money your business is missing."** Foundation stage only — no fake AI. Establish a clean, dark-first, sophisticated fintech shell with feature-oriented architecture that we can extend in subsequent stages.

## Stack decisions (defaults, user opted out of clarification)
- React 19 (CRA + CRACO) + Tailwind + shadcn/ui + Phosphor Icons + Recharts (frontend only for Stage 1)
- Fonts: **Cabinet Grotesk** (headings), **IBM Plex Sans** (body), **JetBrains Mono** (numeric)
- Accent: restrained emerald (`hsl(160 84% 32%)`); amber = warning, rose = critical
- Auth: client-only stub via `localStorage` key `seekprofit.auth` — real auth will land in Stage 2 via the integration playbook agent
- Backend: untouched in Stage 1; FastAPI + MongoDB template ready for Stage 2

## User personas
- **Finance leader / CFO** — wants a defensible read on where profit is leaking and where recovery is possible
- **Revenue operator** — wants an owned queue of high-impact actions
- **Analyst** — wants explainable anomalies with source-linked citations

## Core requirements (static)
- Dark-first premium fintech aesthetic; no gradient/glassmorphism excess
- Feature-oriented folder structure under `src/features/*`
- Reusable component library under `src/components/shared/*` and `src/components/ui/*`
- Left sidebar + top header + main content shell + responsive mobile nav
- Every navigation destination must resolve — placeholder pages allowed, but no broken routes
- Zero console errors, no lorem ipsum, no unused dependencies

## Implemented (Stage 1 — Foundation)
_Date: Feb 2026_

### Architecture
- `src/features/{authentication,overview,revenue-recovery,profit-leaks,opportunities,action-center,data-sources,imports,ai-analysis,reports,settings,system}` — feature slices
- `src/components/layout/{AppShell,Sidebar,Header}.jsx`
- `src/components/shared/{PageHeader,KpiCard,StatBadge,SectionCard,EmptyState,LoadingState,ErrorState,PlaceholderPage,RevenueTrendChart}.jsx`
- `src/config/navigation.js` — single source of truth for sidebar sections
- `src/constants/testIds.js` — canonical `data-testid` registry

### Shell + routes
- `/` → redirect to `/app/overview`
- `/login` → premium two-column login (email/password stub + demo-operator quick sign-in)
- `/app/*` (guarded by `RequireAuth`) → shell with 10 routes wired end-to-end
- `*` → styled NotFoundPage

### Overview dashboard (real content)
- 4 KPI cards (Revenue Recovered, Potential Recovery, Active Profit Leaks, High-Impact Actions)
- Recharts area chart (recovered vs. potential) with dark theme + JetBrains Mono ticks
- Signal feed list with tone-coded badges
- Data quality / Coverage / Analyst-hours strip

### Placeholder pages (Planned — Stage 2)
Revenue Recovery, Profit Leaks, Opportunities, Action Center, Data Sources, Imports, AI Analysis, Reports, Settings — each ships with an eyebrow, title, description and the four features that will land next.

### Quality
- 100% pass on frontend testing agent iteration 1 (all 10 flows)
- 0 console errors (Recharts initial-mount width/height warning is known and filtered)
- Every interactive element carries a `data-testid`

## Prioritized backlog

### P0 — Stage 2 core (next)
- Real authentication (via integration_playbook_expert_v2) — email/password + Google
- FastAPI backend scaffold: workspaces, users, sessions, action items
- Data Sources: first native connector (Stripe or QuickBooks) + Imports (CSV drag-drop)
- Overview wired to real aggregated metrics

### P1 — Feature depth
- Revenue Recovery queue + case detail
- Profit Leaks detector rules + explainability panel
- AI Analysis with source-linked citations (LLM via emergent LLM key)
- Reports with scheduled PDF export

### P2 — Growth polish
- Workspace switcher and multi-tenant scoping
- Roles + audit log
- In-app command palette (⌘K)

## Next tasks (immediate)
1. Kick off Stage 2 auth integration (call integration playbook expert before writing any auth code)
2. Design first backend Mongo models: `Workspace`, `User`, `ActionItem`, `Signal`, `DataSource`
3. Wire Overview KPIs to `/api/overview/metrics` once the backend lands
