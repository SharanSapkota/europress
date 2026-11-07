# TASKS.md: Required deliverables (must all be done)

Every task A to E below MUST be delivered before submission. Each one has: what it is, which data it uses, what we output, how we check it, and where it shows in the portal.
Status lives in PROGRESS.md. A task is "done" only when its check passes and its explanation (Task E) exists.

Data: synthetic dataset pack v1.0.1 (`data/quickstart/public/csv`). Reference docs: `docs/dataset/`. Reference code (read only, never imported): `reference/europress/`.
Rules for all tasks: money in cents, weights in kg, local dates in Europe/Helsinki, never guess an unknown weight, every recommendation is a proposal a person approves, no accusing words.

---

## Task A: What every lift should have cost

**In plain words:** recompute what every lift should have cost under its contract, and the cost per tonne.

- **Data:** `collection_events`, `contract_versions` (version valid on the local service date), `weighbridge_tickets`, `invoice_lines`, `material_classes`, `price_index_monthly`, `quality_assessments`, `quality_grade_rules`.
- **Output per lift:** collection cost, processing cost, penalties, material credit, net, total; cost per tonne; the mass used and its source (weighbridge, invoice quantity, device estimate). Cost per tonne stays empty when the mass is unknown.
- **Rules:** port the charge logic from `reference/europress/` (the baseline scored 1.0 on Task A). Follow `docs/dataset/ECONOMIC_MODEL.md`.
- **Check:** pytest against `api/tests/fixtures/labels_dev_reference_economics.csv` (exact to the cent). Official check: `python -m europress_data.evaluate --task A --pred my_task_a.csv --labels <labels_dev> --split validation`.
- **Portal:** "Our invoice (estimate)" column and line comparison. Phase 1.

## Task B: Irregular lifts and invoice lines

**In plain words:** find the irregular lifts and invoice lines, and do not flag the ones that have a good reason.

- **Data:** Task A output, `invoice_lines`, `collection_events`, `weighbridge_tickets`, `devices`, `material_classes`, telemetry (deduplicated).
- **Find:** weight discrepancy, duplicate line, unmatched line, missing line, uninvoiced collection, wrong surcharge, outdated tariff, weight basis mismatch, cost per tonne high, premature unjustified lift, delayed collection, contamination value loss, rejected load.
- **Do not flag (explained):** combined loads (`loads_on_vehicle` > 1), side waste, stored tares, hygiene limit (biowaste 7 days), maximum interval rule, pre-closure lifts.
- **Output per item:** type, entity, euros at stake (estimate), status (CHECK or EXPLAINED), reason in one sentence, confidence.
- **Compare:** simple rules vs a model. Baseline to beat: macro F1 0.86; weakest family is premature unjustified (1 of 7 found).
- **Check:** `python -m europress_data.evaluate --task B --pred my_task_b.csv --labels <labels_dev> --split validation`. Report "found X of Y", not exact rates (the validation sets are small).
- **Portal:** status chips and "Possible reason" on the Invoices page. Phase 1 (invoice items), then lift items.

## Task B2: Operator scorecard

**In plain words:** build an operator scorecard for punctuality, missed visits, data sharing, billing accuracy and weight differences.

- **Data:** `collection_events` (scheduled vs actual, status), `weighbridge_tickets` (published share, delay), `invoice_lines` + Task A/B results (billing accuracy), device vs ticket differences, `operators`, `sites.region_code`.
- **Output:** one row per `operator_id, region_code, month` plus the scorecard metrics named in `docs/dataset/DATA_DICTIONARY.md` (labels_dev/operator_scorecard).
- **Known from our run:** OP-C shares 45% of tickets with a median delay of 23 days; OP-A 94% in 1.9 days; OP-E 89% in 0.3 days.
- **Check:** `python -m europress_data.evaluate --task B2 --pred my_scorecard.csv --labels <labels_dev> --split all`.
- **Portal:** an "Operator" view with one card per operator. A later phase.

## Task C: Operational decisions for a device

**In plain words:** recommend operational decisions for a device. Schedules and thresholds are SMART's existing domain.

- **Data:** `decision_cases` (device, horizon, candidate and diagnostic actions, `decision_at`), telemetry, `collection_events`, `devices` (policy, thresholds), `material_classes` (max days between collections), `site_calendar`.
- **Rules:** use only data known before `decision_at` (`open_dataset(root, as_of=...)`). Always check hygiene and maximum-interval limits. Watch for actions that look cheap and are not (hidden cost traps). "No action" is a valid answer.
- **Output per case:** chosen actions (subset of `candidate_actions`), expected benefit in euros (estimate), reason, confidence.
- **Check:** score against `labels_dev_decision_truth` / `labels_dev_decision_outcomes` on the dev split. Find the exact evaluate command in the pack before claiming a score.
- **Portal:** a proposal card ("Change trigger to 80%, saves about €X") with Approve / Reject. A later phase.

## Task C2: Operator and contract actions

**In plain words:** recommend dispute an invoice, request weighbridge data, renegotiate, or tender the operator.

- **Data:** Task B results, Task B2 scorecard, `contract_versions`, `decision_cases` (candidate actions), valuation rules in `docs/dataset/ECONOMIC_MODEL.md` section 7.
- **Output:** `case_id, actions`, with a `;`-separated subset of the case's `candidate_actions` (empty = no action), plus the reason and expected value (estimate).
- **Rules:** a difference is not automatically the operator's fault. Prefer "request weighbridge data" before "dispute" when the evidence is weak.
- **Check:** `python -m europress_data.evaluate --task C2 --pred my_actions.csv --labels <labels_dev> --split dev`.
- **Portal:** "Prepare question" on the Invoices page (draft text only, nothing sent). Phase 1 covers dispute and data request drafts.

## Task D: Business case for a new Europress service

**In plain words:** write a business case for a new Europress service. We choose and justify the price and adoption.

- **Service:** SMART Weight subscription (invoice check, true €/t, operator scorecard), with pay-per-tonne lease and operator feed as options.
- **Inputs we set and justify:** price per device per month, cost to serve, adoption rate, realisation rate of found value. Write them in `configs/my_params.yaml` (copied from the pack's `configs/commercial_assumptions.yaml`). Every number is marked as an assumption with a one-line reason.
- **Run:** `python baselines/business_case.py quickstart --params configs/my_params.yaml --out my_business_case` (in the pack).
- **Output:** customer value per device per year (from Tasks A to C2), Europress revenue, payback, and a sensitivity line (what if adoption is half).
- **Check:** every euro traces to a script output or a labelled assumption. Data is synthetic: no real savings claims.

## Task E: Explain everything

**In plain words:** explain everything so a human can check and approve it.

Every number and every flag in the portal and the submission must show:
1. **What:** the value in plain words.
2. **Where from:** the source (weighbridge ticket, invoice line, device estimate, contract version id).
3. **How sure:** a range or a confidence label; "Not enough data" when needed.
4. **Why:** a one-sentence reason, including the explained causes we ruled out.
5. **Who decides:** an Approve / Reject or Mark as OK / Prepare question button. Nothing is sent automatically.
6. **Trail:** every decision is stored with time and user.

Submission docs also list: assumptions, what is untested (no hardware proof, synthetic data, small validation sets), and every third-party library, model, dataset and service with its licence.

---

## Coverage map

| Task | Phase 1 (invoice) | Later |
| --- | --- | --- |
| A | Our invoice per lift | Cost per tonne view |
| B | Invoice items (duplicate, unmatched, weight gap) | Lift items (premature, delayed) |
| B2 | No | Operator scorecard |
| C | No | Device proposals |
| C2 | Dispute / request data drafts | Renegotiate, tender |
| D | No | Business case doc |
| E | Yes, for every invoice item | Yes, for everything |