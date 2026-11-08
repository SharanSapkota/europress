# CLAUDE.md

Customer portal for waste-compactor customers (Since AI Hackathon 2026, Europress challenge). Demo on synthetic data.

## MANDATORY: docs/TASKS.md
Tasks A, B, B2, C, C2, D and E in `docs/TASKS.md` MUST all be delivered. Read it before every phase. Each feature you build must name the task it serves, follow that task's rules, and pass that task's check. Keep their status in PROGRESS.md. Never mark a task done without its check and its explanation (Task E).

## Product (build in this order, small slices)
1. **Invoice comparison**: compare the invoice WE generate (our weight x contract tariff) with the invoice a third-party operator sends. Per pickup and per line.
2. Weights view: pickups with weight, source label, range.
3. Home summary: last pickup sentence + invoice status line.
Add features only when asked.

## Stack
- Monorepo: `/web` (React + TypeScript + Vite), `/api` (Python 3.12 + FastAPI + pydantic), MongoDB via `pymongo`.
- No UI library. Plain CSS with variables. `react-router` and `fetch` only. Ask before adding any dependency.

## API architecture (strict)
`controller -> service -> repository`
- `api/app/controllers/`: FastAPI routers. Parse input, call one service, return DTO. No logic, no DB.
- `api/app/services/`: all business logic. Pure and testable. Repositories injected via constructor.
- `api/app/repositories/`: the only code that touches Mongo. One class per collection.
- `api/app/models/`: pydantic schemas. `api/app/core/`: config, db client.
- Money in integer cents. Weights in kg. Dates ISO 8601 UTC.

## Mongo collections (seed from dataset CSV in `data/quickstart/public/csv`)
One collection per CSV, same name. Generated: `decisions`.
Join key between pickup, ticket and invoice line: `operator_job_ref`. It can contain typos: fall back to contract_id + service_date.
Seed script: `api/scripts/seed.py` (loads every CSV, drops and reloads, never loads labels_dev).

## Invoice comparison rules
- Our weight source order: operator ticket (`allocated_net_kg`) > calibrated device mass > fill estimate. Always store `source` and `range_kg`. Never guess an unknown weight.
- Status per pickup: `MATCH`, `CHECK`, `EXPLAINED`, `NO_DATA`. Tolerance is a config value.
- `EXPLAINED` when `loads_on_vehicle` > 1, side waste, or stored tare. These are normal, not errors.
- Also flag duplicate invoice lines and invoice lines with no matching pickup.
- Euros at stake are always labelled "estimate".
- Only propose. A person approves. Never send anything to the operator automatically. Never use accusing words.

## Endpoints (add as needed)
`GET /api/pickups`, `GET /api/invoices/comparison?period=YYYY-MM`, `GET /api/invoices/comparison/{pickup_id}`, `POST /api/invoices/comparison/{pickup_id}/decision` (body: `ok` | `question`).

## Design tokens (web/src/styles/tokens.css, reference: design/01-dashboard.png … 08-decisions.png; ignore *@2x.png and design/reference)
```
--primary: #0B3253; --primary-dark: #082640; --text: #2C3E50; --muted: #5B6B7B;
--page: #F5F7FA; --card: #FFFFFF; --line: #E3E9EF; --key-bg: #E6EEF7;
--check-bg: #FDF3E0; --check-text: #8A5300; --good-bg: #E3F3E8; --good-text: #1E6B3A;
--check-line: #E0A93B; --tile: #1B4569; --table-head: #EEF2F6; --foot: #7A8A99;
font-family: Inter, Roboto, "Open Sans", sans-serif; tabular numbers.
```
- Header: 72px, gradient primary to primary-dark, padding 0 48px, 36px logo tile, "SMART WEIGHT" 15px 800 .14em. Nav 12px uppercase 600 .12em, 72% white, active white: Dashboard, Invoices, Cost per tonne, Operators, Containers, Value, Decisions.
- Page wrap: max 1340, padding 48, flex column, gap 24. H1 40px 800 uppercase primary; sub text 15px muted.
- Shared components (web/src/components/ui.tsx, styles/base.css): Card, TotalsPanel (3 columns, third on key-bg), StatTile (3px left line: amber = to check, primary otherwise), Chip (disputed, good, neutral, blue, check), InfoIcon (18px "i", dark popover on hover or click), Button (primary, outline; 44px), TableHeader, FootNote. Page-only styles live in styles/app.css and use tokens only.
- No red anywhere. Amber only for CHECK. Say "lift", never "line". Euro amounts that are not billed say "estimate".
- Plain words: "Check this", "Matches", "Estimated". Max 3 actions on a screen.

## Layout
```
/web/src/{pages,components,api,styles}
/api/app/{controllers,services,repositories,models,core}
/api/tests   /api/scripts   /data
```

## Working rules (save tokens)
- Plan in 10 lines or less, then build. One vertical slice at a time (model -> repo -> service -> controller -> UI).
- Read only the files you need. Do not re-read files you just wrote. Do not list or scan the whole repo.
- No explanatory prose, no boilerplate comments, no README unless asked.
- Tests: one small pytest file per service. Run only the tests for the touched module.
- Finish with at most 3 lines: what changed, how to run, next step.
- Data is synthetic. Never claim real savings.

## Commands
- API: `cd api && uvicorn app.main:app --reload` | tests: `pytest api/tests -q`
- Web: `cd web && npm run dev`
- Seed: `python api/scripts/seed.py data/quickstart/public/csv`
- Mongo URI from `MONGO_URI` (default `mongodb://localhost:27017/portal`).