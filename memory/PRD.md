# SeekProfit — Product Memory

## Original problem statement
Build **SeekProfit**, a polished, competition-ready AI-powered financial intelligence SaaS.
Core promise: **"Find the money your business is missing."**

Product blends: profit-leak detection, revenue recovery, financial anomaly detection, AI-powered explanations, and prioritized recommended actions — grounded in real business data.

## Stack
- Backend: FastAPI + Motor (MongoDB), Python 3.11, JWT auth
- Frontend: React 19 (CRA) + Tailwind + shadcn/ui + Phosphor Icons + Recharts
- LLM: Claude Sonnet 4.6 via `emergentintegrations` + `EMERGENT_LLM_KEY`
- Auth: JWT email/password + Emergent-managed Google Sign-in (unified user model)
- Session: JWT bearer token in localStorage key `seekprofit.auth`

## User personas
- **Finance leader / CFO** — wants a defensible read on missing money
- **Revenue operator** — needs an owned queue of high-impact actions
- **Analyst** — needs explainable anomalies with source-linked citations

## Core requirements (static)
- Dark-first premium fintech aesthetic; no gradient/glassmorphism excess
- Feature-oriented folder structure (`src/features/*`)
- Deterministic financial calculations in backend; LLM only interprets & cites
- Every AI finding must include: impact, confidence, urgency, explanation, recommended action, evidence record IDs
- Signals categorized into Revenue Recovery, Profit Leaks, Opportunities — no double-counting
- Seeded demo dataset by default; CSV replacement supported
- Zero console errors, no lorem ipsum

## Implemented (Stage 2 — Real product)
_Date: Feb 2026_

### Backend
- `core/db.py`, `core/security.py` — Mongo client + JWT/bcrypt + auth dependency
- `services/seed.py` — deterministic demo dataset (~200 records: contracts, invoices, payments, vendor bills) with pre-baked leaks + opportunities
- `services/finance.py` — deterministic KPI + trend + priority-score computations
- `services/detectors.py` — rule-based signal detectors: duplicate vendor payments, overlapping subscriptions, unbilled services, late-paying customers, renewal price uplift
- `services/llm_analyst.py` — Claude Sonnet 4.6 wrapper (explains signals + Q&A) with strict grounding on brief data + fallback templates
- `routers/auth.py` — register / login / Google callback / me / invite (lean invite-by-email)
- `routers/onboarding.py` — business setup + seed + reseed
- `routers/overview.py` — KPI cards + trend + top-signal feed
- `routers/signals.py` — list / filter by category / update status / bulk LLM enrichment
- `routers/ai.py` — grounded Q&A with `[rec:record_id]` citations extracted
- `routers/imports.py` — CSV upload with schema mapping → replaces dataset + re-runs detectors
- Mongo indexes created on startup

### Frontend
- `AuthContext` — JWT + Google, persists in localStorage, verifies via `/auth/me`
- `LoginPage` — sign-in / sign-up + "Continue with Google"
- `AuthCallbackPage` — `/auth/callback` reads `session_id` from URL fragment and completes sign-in
- `OnboardingPage` — business setup → triggers backend seed
- `OverviewPage` — all values fetched from `/api/overview`; KPI cards, trend chart (Recharts), signal feed
- `AIAnalysisPage` — Ask SeekProfit panel (with citation chips + cited-records list) + ranked signal list with tabs; on-demand "Enrich with Claude" button
- `CategorySignalsPage` (reused) → Revenue Recovery, Profit Leaks, Opportunities pages
- `SignalCard` — reusable expandable card with explanation, recommended action, evidence records, and action buttons (mark resolved / take action / dismiss)
- `ImportsPage` — CSV upload UI + result summary
- `DataSourcesPage` — demo / CSV state + native connector roadmap
- `SettingsPage` — workspace profile + lean invite-by-email

### Quality
- Deterministic backend math — LLM cannot hallucinate figures
- Every signal carries impact / amount_type (measured|estimated|potential) / confidence / urgency / priority_score
- No double-counting: each record only feeds one category
- CSV workflow validated end-to-end

## Prioritized backlog

### P0 next
- Streaming SSE for Ask SeekProfit (nicer perceived latency)
- Action Center page — unified queue across categories

### P1
- Reports: PDF export with recovered $ + open pipeline
- Roles + granular permissions (owner / admin / analyst / viewer)
- Native connectors: Stripe first (playbook already exists)

### P2
- Audit log
- Command palette (⌘K)
- Multi-workspace switcher

## Next tasks (immediate)
1. Wire the Reports page to real data
2. Ship the Action Center as a unified queue
3. First real connector integration (Stripe) using integration playbook
