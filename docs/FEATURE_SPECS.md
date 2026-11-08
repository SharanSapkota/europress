# FEATURE_SPEC.md: Weight feature tabs (corrected, based on the Step 1 evidence)

All numbers in this file are from `api/scripts/feature_evidence.py` on the quickstart data (465 pickups, 50 devices, about 3 months). The app must compute every number itself; these are examples to check against.

Tags on every figure: OBSERVED, ESTIMATED (with range), SIMULATED (pitch and business case only, never in the app), HYPOTHETICAL (our assumptions in configs/my_params.yaml).

## Navigation (6 tabs)

Invoices · Cost per tonne · Pickups · Site checks · Operators · Fleet & Scales

Header: "SMART WEIGHT" left, Customer select ("All sites") right.

## Feature card (same layout for every feature)

1. Title + status badge (Check this, Worth a check, Good, Not enough data).
2. One plain subtitle: what the feature protects.
3. Explanation: 2-3 everyday sentences. No column names.
4. Three reasoning cards in a row: "What fill % misses" · "What weight shows" · "What you gain".
5. One real example box: site, device, 2 horizontal CSS bars (benchmark vs measured), one result line.
6. Evidence box: tag + range, confidence (High / Medium / Low with pickups used), data used in plain words, neutrality note, "Draft only. Nothing is sent without your approval."
7. Action bar, max 3: Prepare proposal · Not now · Undo.
8. Collapsed "Show calculation and full table".

## Tab: Pickups

### Minimum charge guard (lead feature)
- What: lifts that triggered a minimum charge top-up because the container was too light.
- Evidence: 91 lifts with a top-up, 7,636 € total in 3 months; 23 could have waited without breaking max days or closures.
- Example: COL-00026-0006, 220 kg at lift vs 1,159 kg break-even, 159 € top-up, 4.3 more days was within the 21-day limit.
- Tag: OBSERVED top-ups, ESTIMATED "could have waited".
- Pitch only: MASS_TARGET_TRIGGER is positive in 67 of 161 simulated cases (SIMULATED).
- Note: the PREMATURE_UNJUSTIFIED match (2 of 41) is low because that label is a different problem (unneeded lifts), not minimum charges. Say so.

### Day-0 provisional receipt
- What: the weight and expected credit on the day of pickup, before the scale ticket arrives.
- Show it only where it matters: operators with slow or missing tickets. The median delay is 2 days, so it adds little for fast operators.
- Expected credit uses the device's last known grade (not a fixed B), with a range. Median gap to the final credit is 18% over 172 lifts, so show "expected 150-200 €" style ranges.
- Example: COL-00020-0003, 3,100 kg, expected credit about 175 €, ticket arrived after 82 days, final credit 114 €.
- Tag: ESTIMATED. Words: "provisional", "expected credit". Never "certified".

## Tab: Site checks

### Material left after pickup
- What: lifts where a lot of material stayed in the container.
- Evidence: 17 lifts.
- Example: COL-00024-0050, 2,720 kg before, 710 kg after (26% left), status PARTIAL.
- Tag: ESTIMATED. Exclude devices with a sensor work order within 7 days ("sensor baseline").
- Words: "material stayed in the container". No cause claimed (no weather data).

### Shared truck split
- What: when two of the customer's own containers go on one truck, the operator splits the weight 50/50. Device weights give a fairer split between the customer's sites.
- Evidence: 16 combined weighings, 14,146 kg and 610 € moved between sites.
- Example: WB-OP-A-00034-0009, Hyvinkää site 3 +2,368 kg (+273 €), Porvoo site 6 −2,368 kg (−300 €). The amounts differ because each site has its own contract rates; show that net difference as one line.
- Tag: ESTIMATED. Neutrality note: "This is about your own sites' cost split, not an operator mistake."

### Density check
- What: density at pickup compared with normal for the material.
- Mixed waste below 85% of normal: "Lighter than normal. This often means light packaging is in the general waste. Worth a check." Example: CMP-00026, Kangasala site 1, 289 vs 380 kg/m³ (76%), 10 lifts.
- Cardboard above 115% of normal: "Heavier than normal. On outdoor staging sites this is often wet material."
- No savings figure: the simulated sorting intervention never paid off (0 of 140 cases). Status is always "Worth a check".
- Tag: ESTIMATED ±3.3%.

## Tab: Fleet & Scales

### Truck tare check
- What: trucks whose stored empty weight differs from their weighed empty weight.
- Evidence: 41 vehicles have both, 12 differ by 100 kg or more. Example: OP-B-V04 stored tare 450 kg above weighed.
- Tag: OBSERVED. Feeds the Operators scorecard and the "stored tare" reason on Invoices.
- Separate line: 9 devices whose gap moved after a sensor work order, shown as "Our scale was serviced".

### Equipment right-sizing (Europress sales)
- What: containers that are often full or overflow.
- Evidence: 6 of 50 devices. Example: CMP-00001, DUO 8 to 10 m³, 50 h full, 2 side-waste lifts, about 12 lifts a year avoided.
- Saving = lifts avoided × lift cost from the contract MINUS the extra rental of the bigger unit (HYPOTHETICAL, from configs/my_params.yaml). Show "scaled estimate".
- Limits: COMBI up to 22 m³, DUO up to 30 m³. No model names.

### Value and payback summary
- Customer value per device per year from the tabs above (ESTIMATED, scaled).
- Europress revenue from package prices and adoption in configs/my_params.yaml (HYPOTHETICAL).
- Pitch only: simulated benefits from decision_outcomes (SIMULATED).

## Unchanged tabs
Invoices, Cost per tonne and Operators stay as built.