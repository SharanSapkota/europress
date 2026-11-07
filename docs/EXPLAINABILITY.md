# Task E: Explainability (how the portal meets the judges' rubric)

Smart Weight portal, Europress challenge. All data is synthetic (dataset pack v1.0.1). No figure here is a real saving.

## Rubric mapping

| Criterion | Where it shows in the portal | How it is checked |
|---|---|---|
| Evidence separation | Every amount, weight, ratio and measure on Invoices, Cost per tonne, Operators, Primary ideas (5, 3, 6) and Secondary ideas & Task D (1, 2, 4, 7) has a "Why?" button. Its last line says how sure we are and tags the figure *Observed*, *Estimated* or *Hypothetical* (definitions below). | `api/tests/test_explain.py` and `api/tests/test_weight_ideas_service.py` fail if any shown figure has no source, no confidence or no evidence tag. |
| Traceability | Each invoice row and weight-idea row shows its trail: pickup → job ref → scale ticket → contract version → invoice lines / work orders. Every "Why?" names the source ids (ticket, invoice line, contract version, device, work order). Each decision stores the same ids. | `test_explain.py`, `test_weight_ideas_service.py` |
| Constraints and uncertainty | Cost per tonne and Idea 1 ("Why?" on the main reason and mass trigger): the material's maximum days between pickups; low-fill pickups required by the maximum interval, the 7-day hygiene limit or a pre-closure order (left out as a cause); hours the container was full (overflow risk); share of valid device weight readings; pickups without a scale ticket. Device weights carry ± 3.3 % (and ± 6.5 % in degraded sensor sensitivity). | `test_cost_service.py`, `test_weight_ideas_service.py` |
| Human approval | Every suggestion across Invoices, Operators, Primary ideas (5, 3, 6) and Secondary ideas (1, 2, 4, 7) is a proposal with a reason and a draft; nothing is sent. Decisions (Mark as OK, Prepare question, I sent it, Prepare request, Prepare proposal, Not now) are stored with user, time, the suggestion shown and the numbers behind it. The Decisions page (footer link) lists them and offers Undo. Undo adds a new entry; old entries are never deleted. | `test_decision_service.py`, `test_disputed_status.py`, `test_weight_ideas_service.py` |
| Avoids over-claiming | Our amounts are labelled "estimate". Operator action values, sorting diversion savings, and Task D business case figures are tagged *Hypothetical*: they use published ECONOMIC_MODEL rules and explicit assumptions (`configs/my_params.yaml`) and are not proof of a real saving. Ram bridging (`S40`) is never claimed as a problem (resolved by multi-pressing). | `test_weight_ideas_service.py` |
| Neutral tone | Each flagged item names its likely source: invoice line compared with your contract, device or weighbridge measurement, missing data, or normal operation. Idea 3 and Idea 4 cross-check `maintenance_work_orders` (`WEIGHT_RECALIBRATION`, `WEIGHT_SENSOR_REPLACED`) so compactor sensor offsets are never blamed on the operator. No accusing words appear in the UI or the drafts. | `test_suggestion_service.py`, `test_weight_ideas_service.py` |

## Evidence tags

| Tag | Meaning in this portal | Examples |
|---|---|---|
| Observed | Read directly from a record (operator invoice, scale ticket, the customer's pickup records, contract terms, maintenance work orders) | Operator invoice amounts, ticket weights, on-time share, contract benchmark, work order IDs |
| Estimated | Calculated by us from records | Our invoice, differences, cost per tonne, device weights, measured bulk density (kg/m³), post-lift residual mass %, proportional combined-load split |
| Hypothetical | Depends on assumed probabilities or prices | Expected value of renegotiating or tendering (§7 rules), sorting diversion savings, MASS_TARGET_TRIGGER savings, Task D business case & sensitivity |
| Simulated | Output of the dataset's simulator | Not shown in the portal; used only by the evaluators |

## What remains unproven

- The data is synthetic, so the results show how the method works, not real savings.
- §7 action values and Task D commercial projections assume the published recovery rates, acceptance probabilities, adoption rates and effort costs (`configs/my_params.yaml`). Real negotiations depend on much more.
- No hardware proof. Device weights come from the synthetic sensor model, and its accuracy (±3.3% nominal, ±6.5% degraded stress test) is assumed.
- The validation sets are small: Task B2 has 5 scored rows and Task C2 has 7 dev cases.
- Stored-tare gaps are deconvolved in Idea 4 by comparing `STORED_VEHICLE_TARE` vs. `WEIGHED_TARE` per `vehicle_id` against compactor `maintenance_work_orders`.

## Assumptions

- Mass order: scale ticket, then invoice tonnage, then device estimate. An unknown weight is never guessed.
- Dates use Europe/Helsinki local time, and the tariff version is chosen by the local service date.
- Tolerances (config): 2 % per invoice line, 10 % device vs ticket, cost "N.N× normal" from 1.2, on time within 24 h (2 h in the B2 export, per the data dictionary), 80 % tickets shared.
- Customer view: the first customer, or the configured one (with "All customers" filter on Operators, Primary ideas and Secondary ideas).

## Third-party software and data

| Item | Version | Licence |
|---|---|---|
| FastAPI | 0.162.1 | MIT |
| Starlette | 1.10.0 | BSD-3-Clause |
| pydantic | 2.14.3 | MIT |
| pymongo | 4.19.0 | Apache-2.0 |
| uvicorn | 0.54.0 | BSD-3-Clause |
| React, React DOM | 18.3.1 | MIT |
| react-router | 7.1.1 | MIT |
| Vite, @vitejs/plugin-react | 5.4.11, 4.3.4 | MIT |
| TypeScript | 5.6.3 | Apache-2.0 |
| Inter font (Google Fonts) | | SIL Open Font License 1.1 |
| MongoDB Atlas | service | MongoDB terms of service |
| Europress SMART dataset pack | v1.0.1 | Provided for the hackathon; no licence file in the pack |

No machine learning models and no LLMs are used in the portal.
