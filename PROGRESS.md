## Task status (8 Nov 2026, after the new design parts 1–5)
| Task | Status | Check result | Explanation (Task E) |
|---|---|---|---|
| A | Done | Evaluator 1.0 exact to the cent on every cost column (validation); my_task_a.csv unchanged | "Should cost" popover: WHERE FROM (contract version × weight source and value) + HOW SURE (High/Medium/Low + reason); Cost per tonne page with normal rate from the contract version |
| B | In progress | Invoice items: macro F1 0.538 (validation), same 117 rows before and after; lift items (premature, delayed) still open | Plain reason under each date, a 0,00 € difference is always MATCH, "A difference is not proof of a mistake" |
| B2 | Done | Evaluator 81.42/100 (split all); page uses the same metrics() as the export | Operators cards: on time within 2 h, scale tickets in 7 days, billing accuracy, weight vs our scale, each with its "i" source |
| C | In progress | Containers rules respect max days and site calendar (test passes); no decision_truth evaluator run yet | Containers page: old rule → new rule, estimate with "i", Approve / Not now writes a decision only |
| C2 | Done | Evaluator value capture 1.0 (124,10 € of 124,10 €, dev, 7 cases) | Dispute modal and Prepare request: editable message, evidence stored, nothing sent by the server |
| D | In progress | Value page from configs/my_params.yaml (plan prices, adoption, 500 containers → 46 800 € a year, test passes); business case doc and baselines/business_case.py run still to do | Value page tags: Estimate / Example price; footnote says assumptions, not offers |
| E | Done for all pages | 77 API tests pass (incl. test_explain, dispute evidence, append-only undo); build passes | Every number has an "i" popover; Decisions page keeps time, user, chip and evidence trail; Undo appends |

## Status: Invoices, Cost per tonne and Operators tabs done; Task E pass done; Operators filters done
- A: our invoice exact to the cent; Cost per tonne tab (collection cost per known tonne vs contract benchmark, null when weight unknown).
- B: invoice items with status, possible reason, suggested action (correct line / ask for ticket / none); DISPUTED after "I sent it". Lift items still open.
- B2/C2: Operators tab, 5 measures with Good/Check, one suggested action per operator (section 7 values), drafts only on prepare. Nothing is sent. Filters (Customer incl. all, Site, Period 3m/6m/12m/all or from/to) are kept in the URL; each card shows pickups and months covered, with "not sure yet" under 10 pickups. Tests: 49 pass.
- Period filter elsewhere: `GET /api/costs` accepts `period=3m|6m|12m|all` (API only; its page still shows the last 3 months). Invoices stays one month at a time, so no change.
- E (rubric pass, see `docs/EXPLAINABILITY.md`): every figure has "Why?" with source ids, confidence and an observed/estimated/hypothetical tag; invoice rows show the trail pickup → job → ticket → contract version → lines; cost reasons leave out lifts required by hygiene, max interval or pre-closure and quantify hours full, valid readings and missing tickets; each item names its likely source (invoice vs contract, measurement, missing data, normal); append-only decisions with Undo in Decisions. "About the data" page (footer) maps every rule in ASSUMPTIONS_AND_LIMITATIONS.md to where the portal applies it, and lists the ones not built yet. Tests: 50 pass.

- Weight features (`docs/FEATURE_SPECS.md`), Step 2 done (API + tests, UI after your OK): `/api/pickups` (minimum charge guard, provisional receipt), `/api/site-checks` (material left, shared truck split, density), `/api/fleet` (tare check, right-sizing with HYPOTHETICAL lease from `configs/my_params.yaml`), `/api/value-summary`. One card shape, every figure tagged. Best examples match the spec; tests: 59 pass. Customer value ≈ 273 €/device/yr (scaled estimate) vs a 588 € mid package (HYPOTHETICAL).
- Step 3 UI done: generic `FeatureCard.tsx` + `FeaturePage.tsx`; tabs Pickups, Site checks, Fleet & Scales.
- Each card: badge, 3 reasoning cards, example with 2 CSS bars, tagged figures, evidence box, Prepare proposal / Not now / Undo, calculation table.
- Prepare proposal shows a read-only draft with Copy; decisions go to the shared trail; nothing is sent.
- Not yet: header customer select (API supports `customer_id`), Value summary tab (API only), UI tests (skipped as asked).
- Run: API `cd api && .venv/bin/uvicorn app.main:app --reload`, web `cd web && npm run dev`.
- Dashboard tab (start page `/`; Invoices moved to `/invoices`): 4 tiles (invoice gap, to check, cost per tonne ×, avoidable top-ups) and up to 5 alerts.
- Alerts (2 types, one per container, newest first, max 2 shown): "Cover the container" (outdoor site, deduplicated telemetry: +3 % / 30 kg in 6 h with no compaction and fill steady) and "Check for stuck material" (red, > 15 % left or partial, no sensor work order within 7 days).
- `GET /api/dashboard`, `POST /api/alerts/{id}/seen` (bell count drops); the bell's red dot pulses every 2 s, with no pulse under reduced motion.
- Header customer select drives the Dashboard and the feature tabs; Invoices, Cost per tonne and Operators still use the configured customer.
- CLAUDE.md: red #B42318 allowed for alerts only. Tests: 64 pass.
- One customer per view: `CURRENT_CUSTOMER_ID` (default first customer); every API call takes `customer_id` and optional `site_id`, filtered in the repository layer (`repositories/scope.py`); another customer's site, pickup, invoice line or decision returns 404.
- Header shows the customer name and "All my sites" site select; the "Viewing as (demo only)" switcher sits in the footer. Operators has no customer filter; peer-based renegotiate/tender values are hidden in the customer view. Exports stay unscoped for the evaluators. Tests: 70 pass.
- New design, phase 1 (shell, all tasks): tokens.css replaced; styles/base.css holds the shell and shared components (Card, TotalsPanel, StatTile, Chip, InfoIcon, Button, TableHeader, FootNote); app.css 2 073 → ~1 000 lines, old rules and dead classes removed, tokens only, no red. Header has no bell or site select; nav adds Containers (/api/pickups) and Value (/api/value-summary); Pickups, Site checks, Fleet are off the nav. `npm run build` passes.

- New design, phase 2 (Dashboard, Invoices; Tasks A, B, E): dashboard API takes `period`, returns totals with their "i" popovers, 3 tiles (lifts to check, disputed, cost per tonne) and the next suggested decision (highest yearly value among undecided Task C cards); alerts, bell and the alerts_seen collection removed. Invoices: a 0,00 € difference is always MATCH (Task B items unchanged); rows carry `view`, `ours_note`, `billed_note`; "should cost" popover = WHERE FROM (contract version × weight source and value) + HOW SURE (High, Medium or Low with reason); SUBMIT A DISPUTE saves a question only (`DecisionIn` now accepts "question"). Checks: Task A 1.0 exact on every column (file unchanged), Task B macro F1 0.538 before and after (same 117 rows), every popover has source and confidence in Jul–Sep, 16 tests pass, `npm run build` passes.

- Part 1 done (C2, E): dispute modal (03) saves {question, message} via POST /api/invoices/comparison/{id}/decision with evidence (pickup, our scale ± range, ticket, billed kg, weight source, contract version, amounts); lift turns DISPUTED, server sends nothing. Decisions page (08) with chips, trail boxes, append-only Undo. Check: test_dispute_stores_message_and_all_evidence_and_undo_appends passes (16 API tests), build passes.

- Part 2 done (A): Cost per tonne (04): highlight card (highest ratio, plain main reason), site groups, bar + chip (amber only above normal), lighter rows under 10 weighed pickups, site filter, real site/month counts; "normal" = contract version target_collection_cost_cents_per_t. Check: Task A evaluator 1.0 exact on every column; 8 cost tests pass; build passes.

- Part 3 done (B2, C2): Operators (05): two-column cards, rows use the B2 definitions (on time within 2 h, scale tickets in 7 days, billing accuracy = 100 − over − under %, weight vs our scale = weight_bias_pct), period filter Last 3 months/All/Custom, Prepare request opens the shared message modal and stores message + measures; nothing sent. Check: B2 evaluator 81.42 before and after (same metrics() as the page); 30 operator tests pass; build passes.

- Part 4 done (C, C2): Containers (06): GET /api/containers (ContainersService): order-by-weight rules from the minimum charge guard (fill bar from the latest telemetry), skip-light rule for fixed schedules (only when the next pickup stays within max days), weight-sensor check when scale and tickets differ ≥ 5 % (median of last pickups). APPROVE / BOOK A CHECK / NOT NOW only write a decision. Check: test_rules_respect_max_days_and_site_calendar passes (3 tests), build passes.

- Part 5 done (D + final pass): Value (07) from GET /api/value (value found = invoice items to check or disputed + top-ups that could wait + container size changes, last 3 months; plan cost and Europress view from configs/my_params.yaml). Final pass: "line" wording replaced in UI and API texts, no alert/rain/ice/stuck/bell/phone/avoidable/"Why?" left, no red, every page has its own "Demo data" foot note, under 900 px columns stack and nav links hide. Check: 77 API tests pass, npm run build passes.

| Task | Score | Split | Date |
|---|---|---|---|
| A | 1.0 exact to the cent on every column, 0 fabricated | validation | 2026-11-07 |
| B | found: weight 8/9, surcharge 2/2, unmatched 4/4, missing 1/1, uninvoiced 1/1 (macro F1 0.54, lift families open) | validation | 2026-11-07 |
| B2 | 81.4/100 (exact on 5 of 9 metrics, weight bias 0.26) | all (5 rows) | 2026-11-07 |
| C2 | 100% of best value, renegotiate 1/1, 0 wrong picks | dev (7 cases) | 2026-11-07 |

Decisions: customer from `CUSTOMER_ID` or the first customer; exports use all customers. labels_dev and benchmark are never seeded or read by the app. Mass: ticket, invoice, device; never guessed.
Run: `api/.venv/bin/python api/scripts/seed.py` | `cd api && .venv/bin/uvicorn app.main:app --reload` | `cd web && npm run dev` | `api/.venv/bin/pytest api/tests -q` | exports: `export_tasks.py`, `export_scorecard.py`, `export_actions.py`
Next: Task D business case (rubric: prices and adoption from customer value, with sensitivity), Task B lift items, Task C.
