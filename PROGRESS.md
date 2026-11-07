## Status: Invoices, Cost per tonne, Operators, Primary ideas (5, 3, 6) and Secondary ideas & Task D (1, 2, 4, 7) done; 53 tests pass
- A: our invoice exact to the cent; Cost per tonne tab (collection cost per known tonne vs contract benchmark, null when weight unknown).
- B: invoice items with status, possible reason, suggested action (correct line / ask for ticket / none); DISPUTED after "I sent it".
- B2/C2: Operators tab, 5 measures with Good/Check, one suggested action per operator (section 7 values), drafts only on prepare. Nothing is sent. Filters (Customer incl. all, Site, Period 3m/6m/12m/all or from/to) are kept in the URL; each card shows pickups and months covered, with "not sure yet" under 10 pickups.
- Primary weight ideas (`/primary-ideas`): Idea 5 (multi-stream kg/m³ sorting diverter & Balex/DUO upsell), Idea 3 (post-lift residual mass `device_mass_kg_after` separating physical/frozen waste from sensor zero-offsets via `maintenance_work_orders`), and Idea 6 (combined-load 50/50 split proportional source-weight re-allocator).
- Secondary weight ideas & Task D (`/secondary-ideas`, `docs/BUSINESS_CASE.md`, `configs/my_params.yaml`): Idea 1 (`MASS_TARGET_TRIGGER` & `MIN_CHARGE_TOPUP` break-even guard with zero dependency on ram bridging), Idea 2 (Economic Model §2b Day-0 ±3.3% weight receipt & credit share unlock on recyclable streams), Idea 4 (bipartite deconvolution of hauler vehicle stored-tare vs. compactor sensor calibration), Idea 7 (tonnage-verified compaction force tuning & `COMBI` -> `DUO` right-sizer), plus full Task D 3-tier pricing (€29 / €49 / €110), €8.50/mo cost to serve, 1.6-month payback, and 5-scenario sensitivity analysis.
- E (rubric pass, see `docs/EXPLAINABILITY.md`): every figure across all pages has "Why?" with source ids, confidence and an observed/estimated/hypothetical tag; append-only decisions with Undo in Decisions; "About the data" page maps every rule in ASSUMPTIONS_AND_LIMITATIONS.md. Tests: 53 pass.

| Task | Score | Split | Date |
|---|---|---|---|
| A | 1.0 exact to the cent on every column, 0 fabricated | validation | 2026-11-07 |
| B | found: weight 8/9, surcharge 2/2, unmatched 4/4, missing 1/1, uninvoiced 1/1 (macro F1 0.54, lift families open) | validation | 2026-11-07 |
| B2 | 81.4/100 (exact on 5 of 9 metrics, weight bias 0.26) | all (5 rows) | 2026-11-07 |
| C2 | 100% of best value, renegotiate 1/1, 0 wrong picks | dev (7 cases) | 2026-11-07 |
| D & E | All 7 weight-driven ideas + 3-tier pricing & 5-scenario sensitivity model delivered with full Why? traceability and human approval | quickstart & benchmark | 2026-11-07 |

Decisions: customer from `CUSTOMER_ID` or the first customer; exports use all customers. labels_dev and benchmark are never seeded or read by the app. Mass: ticket, invoice, device; never guessed.
Run: `api/.venv/bin/python api/scripts/seed.py` | `cd api && .venv/bin/uvicorn app.main:app --reload` | `cd web && npm run dev` | `python -m pytest api/tests -q` | exports: `export_tasks.py`, `export_scorecard.py`, `export_actions.py`
