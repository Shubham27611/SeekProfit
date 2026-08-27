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

## Implemented (Stage 3 — Ops, streaming, executive brief)
_Date: Feb 2026_

### Action Center
- Signals now carry `owner_email`, `due_date` and computed `sla_status` (overdue / due_soon / on_track)
- `POST /api/signals/{id}/assign` — auto-derives SLA due date from urgency (high=3d, medium=7d, low=14d), flips status to `in_progress`; supports explicit due_date and unassign
- `GET /api/signals/members` — workspace owner + invited emails
- `GET /api/signals?owner=me` and `?status=in_progress` filters
- `ActionCenterPage` — one queue table with tabs (Queue / In progress / Assigned to me / Resolved), quick-assign dropdown, per-row SLA badge, resolve/dismiss, row expand with explanation + evidence

### Streaming Q&A
- `GET /api/ai/ask/stream` — Server-Sent Events. Emits `event: open`, `event: delta` per token, `event: done` with corrected text + resolved citations. Dead `[rec:…]` tokens stripped server-side
- `lib/aiStream.js` — fetch + ReadableStream client with token-by-token dispatch
- AI Analysis panel shows a "STREAMING…" pill + animated caret while the reply grows, then renders citation chips once done

### Executive Report
- `GET /api/reports/executive` — headline (revenue recovered / open pipeline / records analyzed), 3 category totals with open + resolved amounts, trend series, top 8 actions with owner + due, top customers & vendors, resolved wins
- `ReportsPage` — board-ready layout with a Print / Save PDF button; `@media print` stylesheet strips the app chrome and switches to a light print theme

### Quality
- Testing agent: **14/14 stage-3 tests + 31/31 regression** passing. All frontend flows working. Fixed the 2 medium UI defects found (React fragment key warning; mobile overflow on Action Center header)

## Prioritized backlog

### P0 next
- Zero-fill missing categories in the Executive Report so the layout is stable
- Move signal ordering into the Mongo query (currently sort-after-page)
- Accept Bearer header on the SSE endpoint (keep query token as fallback)

### P1
- Native connectors: Stripe first (playbook already exists)
- CSV → Action Center: keep default SLAs after re-detection
- Reports: scheduled email delivery

### P2
- Roles + granular permissions
- Audit log
- Command palette (⌘K)
- Multi-workspace switcher
