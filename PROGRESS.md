## Status: Invoices, Cost per tonne and Operators tabs done; Task E pass done; Operators filters done
- A: our invoice exact to the cent; Cost per tonne tab (collection cost per known tonne vs contract benchmark, null when weight unknown).
- B: invoice items with status, possible reason, suggested action (correct line / ask for ticket / none); DISPUTED after "I sent it". Lift items still open.
- B2/C2: Operators tab, 5 measures with Good/Check, one suggested action per operator (section 7 values), drafts only on prepare. Nothing is sent. Filters (Customer incl. all, Site, Period 3m/6m/12m/all or from/to) are kept in the URL; each card shows pickups and months covered, with "not sure yet" under 10 pickups. Tests: 49 pass.
- Period filter elsewhere: `GET /api/costs` accepts `period=3m|6m|12m|all` (API only; its page still shows the last 3 months). Invoices stays one month at a time, so no change.
- E (rubric pass, see `docs/EXPLAINABILITY.md`): every figure has "Why?" with source ids, confidence and an observed/estimated/hypothetical tag; invoice rows show the trail pickup → job → ticket → contract version → lines; cost reasons leave out lifts required by hygiene, max interval or pre-closure and quantify hours full, valid readings and missing tickets; each item names its likely source (invoice vs contract, measurement, missing data, normal); append-only decisions with Undo in Decisions. Tests: 50 pass.

| Task | Score | Split | Date |
|---|---|---|---|
| A | 1.0 exact to the cent on every column, 0 fabricated | validation | 2026-11-07 |
| B | found: weight 8/9, surcharge 2/2, unmatched 4/4, missing 1/1, uninvoiced 1/1 (macro F1 0.54, lift families open) | validation | 2026-11-07 |
| B2 | 81.4/100 (exact on 5 of 9 metrics, weight bias 0.26) | all (5 rows) | 2026-11-07 |
| C2 | 100% of best value, renegotiate 1/1, 0 wrong picks | dev (7 cases) | 2026-11-07 |

Decisions: customer from `CUSTOMER_ID` or the first customer; exports use all customers. labels_dev and benchmark are never seeded or read by the app. Mass: ticket, invoice, device; never guessed.
Run: `api/.venv/bin/python api/scripts/seed.py` | `cd api && .venv/bin/uvicorn app.main:app --reload` | `cd web && npm run dev` | `api/.venv/bin/pytest api/tests -q` | exports: `export_tasks.py`, `export_scorecard.py`, `export_actions.py`
Next: Task D business case (rubric: prices and adoption from customer value, with sensitivity), Task B lift items, Task C.
