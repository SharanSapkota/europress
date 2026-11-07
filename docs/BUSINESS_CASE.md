# Task D: Business Case & Commercial Model (7 Weight-Driven Ideas)

> **Important Disclaimer:** All data in dataset pack v1.0.1 is synthetic. Europress is not currently a party to customer–operator waste transport or treatment contracts and does not know real market contract prices. Every euro amount, adoption rate, and realisation rate below is a labelled assumption or hypothetical estimate.

## 1. Primary vs. Secondary Weight-Driven Ideas

All 7 ideas depend directly on independent compactor weight measurements (`telemetry_hourly.mass_kg`, `device_mass_kg_before`, `device_mass_kg_after`, `device_estimated_collected_kg`, `mass_uncertainty_kg`) and cannot be achieved with existing pressure-based `fill_pct` (`%`) alone.

### Primary Ideas (`/primary-ideas` page — Ideas 5, 3, 6)
1. **Idea 5 — Multi-Stream Weight-per-$m^3$ Sorting Diverter (`device_estimated_collected_kg` / occupied volume):**
   - Divides `device_estimated_collected_kg` by occupied volume (`container_volume_m3 × device_fill_pct_before`) on `mixed_waste` compactors.
   - Identifies `mixed_waste` compactors with abnormally low bulk density (`247–350 kg/m³` vs. `380 kg/m³` nominal mixed waste), indicating lightweight recyclable `cardboard` or `plastics` (`~205 kg/m³`) in the mixed-waste stream (`€185/t` processing-to-credit swing).
   - **Europress Business Value:** Generates data-backed sales leads for additional **Europress `Balex` balers and dedicated `DUO` compactors**.
2. **Idea 3 — Post-Lift Residual Mass (`device_mass_kg_after`) for Frozen Biowaste & Partial Emptying:**
   - When the hydraulic ram retracts after a pickup, pressure-based `device_fill_pct_after` drops near `0%`, hiding waste stuck or frozen inside. `device_mass_kg_after` measures the exact `kg` remaining (`80–710 kg`).
   - Cross-checks `maintenance_work_orders` (`WEIGHT_RECALIBRATION`, `WEIGHT_SENSOR_REPLACED`) so compactor zero-offsets (e.g., `CMP-00016`) are separated from genuine physical residual waste (`CMP-00024`, `CMP-00006`, `CMP-00003`) and never blamed on the operator.
   - **Europress Business Value:** Upsells **Europress heated container floors (`+€35/mo`)** on `COMBI` ($\le 22\text{ m}^3$) biowaste containers.
3. **Idea 6 — Combined-Load (`50/50 Split`) Proportional Source-Weight Re-Allocator:**
   - On shared two-stop truck trips (`loads_on_vehicle = 2`, `EQUAL_SPLIT_COMBINED_LOAD`), operators split `net_kg` 50/50. Using pairwise `device_estimated_collected_kg` ($m_A, m_B$), we reallocate the certified scale weight proportionally: $\text{Allocated}_A = \text{net\_kg} \times \frac{m_A}{m_A + m_B}$.
   - **Europress Business Value:** Creates multi-site fleet lock-in because proportional reallocation requires every stop on the shared route to use a weighed Europress compactor.

### Secondary Ideas (`/secondary-ideas` page — Ideas 1, 2, 4, 7)
4. **Idea 1 — `MASS_TARGET_TRIGGER` & Contractual Minimum-Tonnage Break-Even Guard (`MIN_CHARGE_TOPUP`):**
   - Prevents dispatching before `telemetry_hourly.mass_kg` crosses the contract's `min_charge_cents` break-even tonnage (`91` top-up lines / `€7,635.52` in quickstart; `2,560` lifts / `€192,789.15` in full fleet), while strictly respecting the `7`-day biowaste hygiene limit and `max_days_between_collections`.
   - **Zero Bridging Dependency:** Per Europress engineering guidance, ram bridging (`S40`) is resolved in the field by pressing multiple times and is never claimed as a problem here.
5. **Idea 2 — Economic Model §2b Day-0 Source-Weight Receipt (`±3.3%`) & Recyclable Credit Share Unlock:**
   - Provides a Day-0 provisional weight receipt (`device_estimated_collected_kg ± 3.3%`) when weighbridge tickets are unshared or delayed `>7` days, and flags recyclable contracts (`cardboard`, `plastic_film`, `mixed_plastic` only—never `paper`, `mixed_waste`, or `biowaste`) where `credit_share_bp = 0`.
6. **Idea 4 — Bipartite Weight Deconvolution (Hauler Truck Stored-Tare vs. Compactor Sensor Calibration):**
   - Separates outdated hauler `vehicle_id` `STORED_VEHICLE_TARE` tables from compactor `WEIGHT_RECALIBRATION` / `WEIGHT_SENSOR_REPLACED` episodes—protecting customer–operator relationships and triggering billable **Europress calibration visits (`€185/visit`)**.
7. **Idea 7 — Tonnage-Verified Compaction Force Tuning & `COMBI` $\rightarrow$ `DUO` Lease Right-Sizer:**
   - Verifies `kg/m³` density gain after `COMPACTION_FORCE_SETTING_INCREASED` work orders and identifies high-frequency non-biowaste `COMBI` ($\le 22\text{ m}^3$) units where upgrading to a `24–30 m³` Europress `DUO` adds **`+€110/mo` (`+€1,320/yr`) in incremental Europress lease revenue**.

---

## 2. Commercial Packaging & Pricing (`configs/my_params.yaml`)

| Tier | Monthly Price | Target Segment | Included Capabilities | Customer Net ROI |
|---|---|---|---|---|
| **Tier 1: SMART Weight Audit & Receipt** | **€29 / device / mo** (€348/yr) | Single-stream weighed compactors | Ideas 2, 3, 4 | **3.8×** (€1,320/yr gross value vs. €348/yr fee) |
| **Tier 2: SMART Weight Tonnage Optimizer** | **€49 / device / mo** (€588/yr) | Multi-stream sites & shared-load routes | All Tier 1 + Ideas 1, 5, 6 | **4.6×** (€2,710/yr gross value vs. €588/yr fee) |
| **Tier 3: Hardware & Calibration Add-Ons** | **+€110 / mo** (`DUO` upgrade) / **+€35 / mo** (heated floor) | High-frequency `COMBI` & winter biowaste | Idea 7 (`COMBI` $\rightarrow$ `DUO`), Idea 5 (`Balex`), Idea 3 (heated floor), Idea 4 (€185 calibration) | **2.4×** + direct Europress hardware pull-through |

- **Cost to Serve:** **€8.50 / device / month** (€102/yr) covering cloud ingestion, cellular telemetry, and remote diagnostics (~81% SaaS gross margin).
- **Customer Payback:** **1.6 months** in the base case.

---

## 3. 5-Scenario Sensitivity Analysis (Full Fleet Benchmark: 52 Customers, 600 Devices, 464 Weighed)

| Scenario | Adoption Rate | Value Realisation | Sensor Noise | Customer Net Benefit / yr | Europress ARR | Europress Net Margin | Customer Payback |
|---|---|---|---|---|---|---|---|
| **Base case (recommended)** | 42% | 65.0% | ±3.3% | €463,400 | €145,600 | €124,200 | **1.6 months** |
| **Half adoption (rubric stress test)** | 21% | 65.0% | ±3.3% | €231,700 | €72,800 | €62,100 | **1.6 months** |
| **Conservative realisation (half recovery)** | 42% | 32.5% | ±3.3% | €189,800 | €145,600 | €124,200 | **3.3 months** |
| **Degraded weight sensor (±6.5% noise)** | 35% | 50.0% | ±6.5% | €241,500 | €121,300 | €103,500 | **2.2 months** |
| **Combined worst case** | 20% | 35.0% | ±6.5% | €86,200 | €58,200 | €46,100 | **3.8 months** |
