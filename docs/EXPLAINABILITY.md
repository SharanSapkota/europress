# Task E: Explainability (how the portal meets the judges' rubric)

Smart Weight portal, Europress challenge. All data is synthetic (dataset pack v1.0.1). No figure here is a real saving.

## Rubric mapping

| Criterion | Where it shows in the portal | How it is checked |
|---|---|---|
| Evidence separation | Every amount, weight, ratio and measure has a "Why?" button. Its last line says how sure we are and tags the figure *Observed*, *Estimated* or *Hypothetical* (definitions below). | `api/tests/test_explain.py` fails if any shown figure has no source, no confidence or no evidence tag. |
| Traceability | Each invoice row shows its trail: pickup → job ref → scale ticket → contract version → invoice lines. Every "Why?" names the source ids (ticket, invoice line, contract version, device). Each decision stores the same ids. | `test_explain.py` checks that each row's trail matches its contract version and invoice lines. |
| Constraints and uncertainty | Cost per tonne, "Why?" on the main reason: the material's maximum days between pickups; low-fill pickups required by the maximum interval, the 7-day hygiene limit or a pre-closure order (left out as a cause); hours the container was full (overflow risk); share of valid device weight readings; pickups without a scale ticket. Device weights carry ± 3.3 %. "Sure" needs 10 pickups with a known weight. | `test_cost_service.py` |
| Human approval | Every suggestion is a proposal with a reason and a draft; nothing is sent. Decisions (Mark as OK, Prepare question, I sent it, Prepare request, Not now) are stored with user, time, the suggestion shown and the numbers behind it. The Decisions page (footer link) lists them and offers Undo. Undo adds a new entry; old entries are never deleted. | `test_decision_service.py`, `test_disputed_status.py` |
| Avoids over-claiming | Our amounts are labelled "estimate". Operator action values are tagged *Hypothetical*: they use the published ECONOMIC_MODEL §7 rules and are not proof of a saving. What remains unproven is listed below. | |
| Neutral tone | Each flagged item names its likely source: invoice line compared with your contract, device or weighbridge measurement, missing data, or normal operation. "Weight vs ours" says a gap can come from the device, the weighbridge or a shared truck. No accusing words appear in the UI or the drafts. | `test_suggestion_service.py` checks the drafts for accusing words. |

## Evidence tags

| Tag | Meaning in this portal | Examples |
|---|---|---|
| Observed | Read directly from a record (operator invoice, scale ticket, the customer's pickup records, contract terms) | Operator invoice amounts, ticket weights, on-time share, contract benchmark |
| Estimated | Calculated by us from records | Our invoice, differences, cost per tonne, device weights, lines to check |
| Hypothetical | Depends on assumed probabilities or prices | Expected value of renegotiating or tendering (§7 rules) |
| Simulated | Output of the dataset's simulator | Not shown in the portal; used only by the evaluators |

## What remains unproven

- The data is synthetic, so the results show how the method works, not real savings.
- §7 action values assume the published recovery rates, acceptance probabilities and effort costs. Real negotiations depend on much more.
- No hardware proof. Device weights come from the synthetic sensor model, and its accuracy is assumed.
- The validation sets are small: Task B2 has 5 scored rows and Task C2 has 7 dev cases.
- Stored-tare gaps are shown as "Check this" by choice. The docs list stored tares as explainable, but some stored tares in the data are out of date.
- Not built yet: Task B lift items (premature, delayed), Task C device decisions and Task D business case.

## Assumptions

- Mass order: scale ticket, then invoice tonnage, then device estimate. An unknown weight is never guessed.
- Dates use Europe/Helsinki local time, and the tariff version is chosen by the local service date.
- Tolerances (config): 2 % per invoice line, 10 % device vs ticket, cost "N.N× normal" from 1.2, on time within 24 h (2 h in the B2 export, per the data dictionary), 80 % tickets shared.
- Customer view: the first customer, or the configured one. The evaluator exports use all customers.

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
