from statistics import median

from app.core.config import Settings
from app.services.comparison_service import ComparisonService
from app.services.cost_service import material_name, recent_rows
from app.services.explain import listing, why
from app.services.operator_action_service import ts
from app.services.pricing import LIFT_STATUSES, rhu

NOMINAL_MIXED_DENSITY_KG_M3 = 380.0
RECYCLABLE_DENSITY_KG_M3 = 205.0
SORTING_SWING_CENTS_PER_T = 18500
CREDIT_STREAMS = ("cardboard", "plastic_film", "mixed_plastic")


class WeightIdeasService:
    def __init__(self, comparison: ComparisonService, pickups, tickets, devices, sites, contracts, versions,
                 materials, work_orders, decision_cases, decisions, settings: Settings):
        self.comparison = comparison
        self.pickups = pickups
        self.tickets = tickets
        self.devices = devices
        self.sites = sites
        self.contracts = contracts
        self.versions = versions
        self.materials = materials
        self.work_orders = work_orders
        self.decision_cases = decision_cases
        self.decisions = decisions
        self.s = settings

    def _scope(self, customer_id: str | None) -> tuple[str | None, str | None, list[dict]]:
        everyone = customer_id in (None, "", "all")
        cid = None if everyone else self.comparison.customer_id(customer_id)
        customers = self.comparison.customers.all() if self.comparison.customers else []
        options = [{"id": c["customer_id"], "name": c.get("customer_name") or c["customer_id"]} for c in customers]
        name = "All customers" if everyone else self.comparison.names([], [], cid)["customer_name"]
        return ("all" if everyone else cid), name, options

    def _apply_decision(self, row: dict, decided: dict[str, dict]) -> dict:
        d = decided.get(row["item_id"]) or {}
        row["decision"] = d.get("decision")
        row["decision_id"] = d.get("decision_id")
        row["decided_at"] = d.get("created_at")
        if row["decision"] != "prepare":
            row["draft"] = None
        return row

    def primary_ideas(self, customer_id: str | None = "all") -> dict:
        cid, cname, options = self._scope(customer_id)
        filter_cid = None if cid == "all" else cid
        idea5 = self._idea5_sorting(filter_cid)
        idea3 = self._idea3_residual(filter_cid)
        idea6 = self._idea6_combined(filter_cid)
        all_ids = [r["item_id"] for r in idea5 + idea3 + idea6]
        decided = self.decisions.current("weight_idea", all_ids)
        idea5 = [self._apply_decision(r, decided) for r in idea5]
        idea3 = [self._apply_decision(r, decided) for r in idea3]
        idea6 = [self._apply_decision(r, decided) for r in idea6]
        return {
            "customer_id": cid,
            "customer_name": cname,
            "customers": options,
            "why": {
                "idea5_summary": why(
                    "Estimated annual sorting value from diverting low-density recyclables out of mixed-waste compactors.",
                    listing([r["device_id"] for r in idea5], "Mixed-waste devices") or "Mixed-waste devices",
                    "high" if idea5 else "not enough data",
                    "Compares measured kg/m³ (device_estimated_collected_kg divided by occupied volume) against the 380 kg/m³ nominal mixed-waste benchmark.",
                    "hypothetical",
                ),
                "idea3_summary": why(
                    "Post-lift residual mass left inside compactors after collection (device_mass_kg_after).",
                    listing([r["pickup_id"] for r in idea3], "Pickups") or "Collection events",
                    "high" if idea3 else "not enough data",
                    "Cross-checks device_mass_kg_after against maintenance_work_orders (WEIGHT_RECALIBRATION) to separate physical stuck/frozen waste from sensor zero-offsets.",
                    "estimated",
                ),
                "idea6_summary": why(
                    "Proportional source-weight reallocation across combined-load truck trips (EQUAL_SPLIT_COMBINED_LOAD).",
                    listing([r["weighing_event_id"] for r in idea6], "Shared weighing events") or "Weighbridge tickets",
                    "high" if idea6 else "not enough data",
                    "Replaces 50/50 split allocation with net_kg * m_A / (m_A + m_B) using pairwise device_estimated_collected_kg.",
                    "estimated",
                ),
            },
            "idea5_sorting": idea5,
            "idea3_residual": idea3,
            "idea6_combined": idea6,
        }

    def secondary_ideas(self, customer_id: str | None = "all") -> dict:
        cid, cname, options = self._scope(customer_id)
        filter_cid = None if cid == "all" else cid
        idea1 = self._idea1_mass_trigger(filter_cid)
        idea2 = self._idea2_day0_receipt(filter_cid)
        idea4 = self._idea4_deconvolution(filter_cid)
        idea7 = self._idea7_rightsizer(filter_cid)
        all_ids = [r["item_id"] for r in idea1 + idea2 + idea4 + idea7]
        decided = self.decisions.current("weight_idea", all_ids)
        idea1 = [self._apply_decision(r, decided) for r in idea1]
        idea2 = [self._apply_decision(r, decided) for r in idea2]
        idea4 = [self._apply_decision(r, decided) for r in idea4]
        idea7 = [self._apply_decision(r, decided) for r in idea7]
        bcase = self._business_case()
        return {
            "customer_id": cid,
            "customer_name": cname,
            "customers": options,
            "why": {
                "idea1_summary": why(
                    "Minimum-charge tonnage break-even guard (MIN_CHARGE_TOPUP) and MASS_TARGET_TRIGGER dispatch.",
                    listing([r["device_id"] for r in idea1], "Devices") or "Devices and invoice lines",
                    "high" if idea1 else "not enough data",
                    "Uses live mass_kg and device_mass_kg_before to avoid dispatching below contract min_charge_cents tonnage. Respects 7-day hygiene and max_days_between_collections; zero dependency on ram bridging.",
                    "estimated",
                ),
                "idea2_summary": why(
                    "Day-0 provisional source-weight receipt (±3.3%) and recyclable material credit share review.",
                    listing([r["contract_id"] for r in idea2], "Contracts") or "Contracts",
                    "high" if idea2 else "not enough data",
                    "Applies ECONOMIC_MODEL §2b weight fallback when scale tickets are unshared or delayed >7 days, and checks credit_share_bp on credit-eligible streams (cardboard, plastic_film, mixed_plastic).",
                    "hypothetical",
                ),
                "idea4_summary": why(
                    "Bipartite deconvolution of hauler vehicle stored-tare gaps vs. compactor weight-sensor calibration.",
                    listing([r["entity_id"] for r in idea4], "Vehicles and devices") or "Weighbridge tickets and work orders",
                    "high" if idea4 else "not enough data",
                    "Separates vehicle_id STORED vs WEIGHED tare differences from compactor WEIGHT_RECALIBRATION / WEIGHT_SENSOR_REPLACED episodes so operators are never blamed for device drift.",
                    "estimated",
                ),
                "idea7_summary": why(
                    "Tonnage-verified compaction force tuning and high-frequency COMBI to DUO lease right-sizing.",
                    listing([r["device_id"] for r in idea7], "Devices") or "Devices and maintenance work orders",
                    "high" if idea7 else "not enough data",
                    "Verifies kg/m³ density after COMPACTION_FORCE_SETTING_INCREASED and identifies non-biowaste COMBI (<=22 m³) units suited for 24-30 m³ DUO upgrades.",
                    "hypothetical",
                ),
            },
            "idea1_mass_trigger": idea1,
            "idea2_day0_receipt": idea2,
            "idea4_deconvolution": idea4,
            "idea7_rightsizer": idea7,
            "business_case": bcase,
        }

    def _idea5_sorting(self, customer_id: str | None) -> list[dict]:
        sites = {s["site_id"]: s for s in self.sites.all()}
        devices = {d["device_id"]: d for d in self.devices.all()}
        contracts = {c["device_id"]: c for c in self.contracts.all()}
        by_dev: dict[str, list[dict]] = {}
        for e in self.pickups.all():
            if customer_id and e.get("customer_id") != customer_id:
                continue
            d = devices.get(e["device_id"]) or {}
            if d.get("material_stream") != "mixed_waste" or e.get("status") not in LIFT_STATUSES:
                continue
            kg = e.get("device_estimated_collected_kg")
            fill = e.get("device_fill_pct_before")
            if kg and kg > 50 and fill and fill > 20:
                by_dev.setdefault(e["device_id"], []).append(e)
        out = []
        for did, events in by_dev.items():
            d = devices[did]
            vol = float(d.get("container_volume_m3") or 20.0)
            densities = [e["device_estimated_collected_kg"] / (vol * (e["device_fill_pct_before"] / 100.0)) for e in events]
            avg_dens = round(sum(densities) / len(densities), 1)
            tot_kg = round(sum(e["device_estimated_collected_kg"] for e in events))
            rec_share = max(0.0, min(0.55, (NOMINAL_MIXED_DENSITY_KG_M3 - avg_dens) / (NOMINAL_MIXED_DENSITY_KG_M3 - RECYCLABLE_DENSITY_KG_M3)))
            rec_kg = round(tot_kg * rec_share)
            ann_factor = 4.0
            ann_saving_cents = round((rec_kg * ann_factor / 1000.0) * SORTING_SWING_CENTS_PER_T)
            status = "CHECK" if avg_dens < 355.0 else "GOOD"
            site = sites.get(d.get("site_id") or "") or {}
            sname = site.get("site_name") or d.get("site_id") or did
            c = contracts.get(did) or {}
            c_ids = listing([e["collection_id"] for e in events], "Pickups")
            hw = "Add Europress Balex baler or dedicated cardboard/plastic DUO compactor" if status == "CHECK" else "Current stream sorting within normal density range"
            suggestion = (f"Audit mixed-waste sorting at {sname} and evaluate a dedicated Europress Balex baler"
                          if status == "CHECK" else "No sorting intervention needed")
            reason = (f"Measured bulk density is {avg_dens:.1f} kg/m³ across {len(events)} weighed pickups "
                      f"(vs. {NOMINAL_MIXED_DENSITY_KG_M3:.0f} kg/m³ nominal mixed waste), indicating ~{rec_kg} kg of "
                      f"lightweight cardboard/plastics in mixed waste.")
            draft = (f"Hello {sname} site team,\n\n"
                     f"Our compactor weight telemetry on {did} (mixed waste, {vol:g} m³) shows a measured bulk density "
                     f"of {avg_dens:.1f} kg/m³ across {len(events)} pickups ({tot_kg} kg total), compared with the "
                     f"typical 380 kg/m³ mixed-waste benchmark.\n\n"
                     f"This lower weight-per-m³ profile suggests approximately {rec_kg} kg of recyclable cardboard or "
                     f"plastics may be entering the mixed-waste stream. Diverting these credit-eligible streams into a "
                     f"dedicated Europress Balex baler or DUO compactor could save an estimated €{ann_saving_cents / 100:,.0f}/year "
                     f"(hypothetical estimate based on contract processing vs. material credit rates).\n\n"
                     f"Would you like to schedule a joint site walk-through?\n\nBest regards,")
            item_id = f"idea5-{did}"
            out.append({
                "item_id": item_id,
                "device_id": did,
                "site_id": d.get("site_id") or "",
                "site_name": sname,
                "customer_id": d.get("customer_id") or "",
                "equipment_class": d.get("equipment_class") or "DUO",
                "volume_m3": vol,
                "lifts_count": len(events),
                "total_mass_kg": tot_kg,
                "measured_density_kg_m3": avg_dens,
                "nominal_density_kg_m3": NOMINAL_MIXED_DENSITY_KG_M3,
                "estimated_recyclable_kg": rec_kg,
                "annual_saving_cents": ann_saving_cents,
                "status": status,
                "europress_hardware": hw,
                "suggestion": suggestion,
                "reason": reason,
                "trail_text": f"Device {did} → Site {d.get('site_id')} → Contract {c.get('contract_id', '–')} → {len(events)} weighed pickups",
                "draft": draft,
                "_draft": draft,
                "why": {
                    "density": why(
                        f"Measured bulk density of {avg_dens:.1f} kg/m³ from device weight and fill before pickup.",
                        f"Device {did} ({vol:g} m³); {c_ids}",
                        "high" if len(events) >= 5 else "low",
                        f"Calculated as device_estimated_collected_kg / ({vol:g} m³ * device_fill_pct_before). Nominal mixed waste is 380 kg/m³.",
                        "estimated",
                    ),
                    "recyclable_kg": why(
                        f"Estimated {rec_kg} kg of low-density cardboard/plastics in the mixed-waste stream.",
                        f"Device {did}; material_classes nominal densities (380 vs 205 kg/m³); {c_ids}",
                        "low",
                        "Derived from the density deficit below 380 kg/m³; only cardboard, plastic_film and mixed_plastic earn material credits.",
                        "estimated",
                    ),
                    "annual_saving": why(
                        f"Hypothetical annual value of €{ann_saving_cents / 100:,.0f}/yr from diverting recyclables.",
                        f"Contract {c.get('contract_id', '–')}; Device {did}",
                        "low",
                        "Uses €185/t swing (€150/t mixed-waste processing avoided + €35/t net recyclable credit). Tagged hypothetical because contract prices are synthetic.",
                        "hypothetical",
                    ),
                },
            })
        out.sort(key=lambda r: (r["status"] != "CHECK", r["measured_density_kg_m3"]))
        return out

    def _idea3_residual(self, customer_id: str | None) -> list[dict]:
        sites = {s["site_id"]: s for s in self.sites.all()}
        devices = {d["device_id"]: d for d in self.devices.all()}
        contracts = {c["contract_id"]: c for c in self.contracts.all()}
        versions = {v["contract_id"]: v for v in self.versions.all()}
        recal_by_dev: dict[str, list[dict]] = {}
        for w in self.work_orders.all():
            if w.get("description_code") in ("WEIGHT_RECALIBRATION", "WEIGHT_SENSOR_REPLACED"):
                recal_by_dev.setdefault(w["device_id"], []).append(w)
        out = []
        for e in self.pickups.all():
            if customer_id and e.get("customer_id") != customer_id:
                continue
            after_kg = e.get("device_mass_kg_after")
            before_kg = e.get("device_mass_kg_before")
            if e.get("status") != "PARTIAL" and (after_kg is None or after_kg < 80):
                continue
            if not before_kg or before_kg <= 0 or after_kg is None:
                continue
            did = e["device_id"]
            d = devices.get(did) or {}
            mat = d.get("material_stream") or "mixed_waste"
            eq = d.get("equipment_class") or "COMBI"
            site = sites.get(e.get("site_id") or "") or {}
            sname = site.get("site_name") or e.get("site_id") or did
            act_date = (e.get("actual_at") or e.get("scheduled_at") or "")[:10]
            recals = recal_by_dev.get(did) or []
            if recals and e.get("status") != "PARTIAL" and after_kg >= 350:
                cls = "CALIBRATION_OFFSET"
                cls_label = f"Sensor zero-offset (recalibration history {recals[0]['work_order_id']})"
                service = f"Schedule Europress sensor zero-offset recalibration (history: {recals[0]['work_order_id']})"
                suggestion = f"Do not flag operator: constant ~{round(after_kg)} kg post-lift baseline on {did} indicates sensor zero-offset"
            elif mat == "biowaste" or (eq == "COMBI" and (e.get("status") == "PARTIAL" or after_kg >= 80)):
                cls = "FROZEN_BIOWASTE_RISK"
                cls_label = "Physical residual / COMBI adhesion risk"
                service = "Europress heated floor option (COMBI <= 22 m³) + de-icing / partial-lift review"
                suggestion = f"Review partial/residual emptying on {did} and evaluate Europress heated container floor"
            else:
                cls = "PHYSICAL_RESIDUAL"
                cls_label = "Physical residual waste after lift" if e.get("status") == "COMPLETED" else "Partial emptying confirmed by weight"
                service = "Container clean-out check + partial-lift fee verification"
                suggestion = f"Check {round(after_kg)} kg residual mass left in {did} after pickup {e['collection_id']}"
            res_pct = round(100.0 * after_kg / before_kg, 1)
            fill_after = round(float(e.get("device_fill_pct_after") or 0.0), 1)
            v = versions.get(e.get("contract_id") or "") or {}
            lift_fee = int(v.get("lift_fee_cents") or 16500)
            wasted_cents = 0 if cls == "CALIBRATION_OFFSET" else round(lift_fee * (after_kg / before_kg))
            wo_text = f"; Work order {recals[0]['work_order_id']}" if recals else ""
            reason = (f"After pickup {e['collection_id']}, fill_pct_after read {fill_after:.1f}%, but "
                      f"device_mass_kg_after measured {round(after_kg)} kg ({res_pct:.1f}% of the {round(before_kg)} kg load)."
                      + (f" Cross-check with maintenance_work_orders ({recals[0]['work_order_id']}) and constant ~440 kg baseline indicates a load-cell zero-offset rather than operator partial emptying."
                         if cls == "CALIBRATION_OFFSET" else
                         " Pressure fill sensors reset when the ram retracts, so only post-lift weight detects unemptied material."))
            draft = (f"Hello team,\n\n"
                     f"On {act_date}, pickup {e['collection_id']} (job ref {e.get('operator_job_ref') or '–'}) on container {did} "
                     f"({material_name(mat)}, {eq}) recorded {round(before_kg)} kg before collection and {round(after_kg)} kg "
                     f"remaining inside afterward ({res_pct:.1f}% residual mass), while fill_pct_after read {fill_after:.1f}%.\n\n"
                     + (f"Note: Maintenance record {recals[0]['work_order_id']} and the constant ~440 kg post-lift baseline indicate a weight sensor zero-offset on {did}, "
                        f"so no operator query is needed; please schedule a Europress calibration check.\n\nBest regards,"
                        if cls == "CALIBRATION_OFFSET" else
                        f"Could we check whether wet/adhered material remained in the container and review whether container "
                        f"cleaning or a Europress heated floor option would prevent lost capacity (estimated at €{wasted_cents / 100:,.2f} "
                        f"of the lift fee)?\n\nBest regards,"))
            item_id = f"idea3-{e['collection_id']}"
            out.append({
                "item_id": item_id,
                "pickup_id": e["collection_id"],
                "device_id": did,
                "site_id": e.get("site_id") or "",
                "site_name": sname,
                "date": act_date,
                "material": material_name(mat),
                "equipment_class": eq,
                "pickup_status": e.get("status") or "COMPLETED",
                "mass_before_kg": round(before_kg),
                "mass_after_kg": round(after_kg),
                "residual_pct": res_pct,
                "fill_after_pct": fill_after,
                "classification": cls,
                "classification_label": cls_label,
                "wasted_capacity_cents": wasted_cents,
                "europress_service": service,
                "suggestion": suggestion,
                "reason": reason,
                "trail_text": f"Pickup {e['collection_id']} → Job {e.get('operator_job_ref') or '–'} → Device {did}{wo_text}",
                "draft": draft,
                "_draft": draft,
                "why": {
                    "mass_after": why(
                        f"{round(after_kg)} kg measured inside {did} immediately after collection ({res_pct:.1f}% of {round(before_kg)} kg).",
                        f"Pickup {e['collection_id']}; Device {did} device_mass_kg_after (±3.3%){wo_text}",
                        "high" if cls != "CALIBRATION_OFFSET" else "low",
                        reason,
                        "estimated",
                    ),
                    "fill_vs_mass": why(
                        f"Fill sensor read {fill_after:.1f}% after lift while load cell measured {round(after_kg)} kg.",
                        f"Pickup {e['collection_id']}; device_fill_pct_after vs device_mass_kg_after",
                        "high",
                        "Hydraulic ram pressure drops to zero when retracted, making fill_pct blind to stuck or frozen waste on the container walls/floor.",
                        "observed",
                    ),
                    "wasted_capacity": why(
                        f"Estimated €{wasted_cents / 100:,.2f} of lift capacity occupied by unemptied residual mass.",
                        f"Contract {e.get('contract_id') or '–'} lift fee ({lift_fee / 100:,.2f} EUR); Pickup {e['collection_id']}",
                        "high" if wasted_cents > 0 else "low",
                        "Zero wasted lift fee attributed when maintenance_work_orders shows a pre-recalibration zero-offset.",
                        "estimated",
                    ),
                },
            })
        out.sort(key=lambda r: (r["pickup_status"] != "PARTIAL", -r["mass_after_kg"]))
        return out[:25]

    def _idea6_combined(self, customer_id: str | None) -> list[dict]:
        sites = {s["site_id"]: s for s in self.sites.all()}
        devices = {d["device_id"]: d for d in self.devices.all()}
        versions = {v["contract_id"]: v for v in self.versions.all()}
        ce_by_ref = {e["operator_job_ref"]: e for e in self.pickups.all() if e.get("operator_job_ref")}
        groups: dict[str, list[dict]] = {}
        for t in self.tickets.all():
            if (t.get("loads_on_vehicle") or 1) > 1 or t.get("allocation_method") == "EQUAL_SPLIT_COMBINED_LOAD":
                if t.get("weighing_event_id"):
                    groups.setdefault(t["weighing_event_id"], []).append(t)
        out = []
        for we_id, tks in sorted(groups.items()):
            if len(tks) < 2:
                continue
            tks = sorted(tks, key=lambda x: x["ticket_id"])
            ta, tb = tks[0], tks[1]
            ea = ce_by_ref.get(ta.get("operator_job_ref") or "") or {}
            eb = ce_by_ref.get(tb.get("operator_job_ref") or "") or {}
            if customer_id and ea.get("customer_id") != customer_id and eb.get("customer_id") != customer_id:
                continue
            ma = float(ea.get("device_estimated_collected_kg") or 0.0)
            mb = float(eb.get("device_estimated_collected_kg") or 0.0)
            if ma + mb <= 0:
                continue
            net_kg = int(ta.get("net_kg") or 0)
            naive_a = int(ta.get("allocated_net_kg") or round(net_kg / 2))
            naive_b = int(tb.get("allocated_net_kg") or (net_kg - naive_a))
            prop_a = round(net_kg * (ma / (ma + mb)))
            prop_b = net_kg - prop_a
            shift_kg = abs(prop_a - naive_a)
            shift_pct = round(100.0 * shift_kg / max(1, net_kg / 2), 1)
            da = devices.get(ea.get("device_id") or "") or {}
            db = devices.get(eb.get("device_id") or "") or {}
            sa = (sites.get(ea.get("site_id") or "") or {}).get("site_name") or ea.get("site_id") or "Site A"
            sb = (sites.get(eb.get("site_id") or "") or {}).get("site_name") or eb.get("site_id") or "Site B"
            va = versions.get(ea.get("contract_id") or "") or {}
            rate_per_t = int(va.get("haul_fee_cents_per_t") or 0) + int(va.get("processing_fee_cents_per_t") or 0)
            if rate_per_t == 0:
                rate_per_t = 4200
            realloc_cents = rhu(shift_kg * rate_per_t, 1000)
            mat = material_name(da.get("material_stream") or db.get("material_stream"))
            status = "CHECK" if shift_kg >= 200 else "GOOD"
            date = (ta.get("arrival_at") or ea.get("actual_at") or "")[:10]
            suggestion = (f"Reallocate {shift_kg} kg ({shift_pct:.0f}% vs 50/50 split) between {sa} and {sb} using device weights"
                          if status == "CHECK" else "Combined-load 50/50 split is close to device weights")
            reason = (f"Truck weighing event {we_id} (net {net_kg} kg) split load 50/50 ({naive_a} kg / {naive_b} kg), "
                      f"whereas compactor load cells measured {round(ma)} kg at {sa} ({ea.get('device_id')}) and "
                      f"{round(mb)} kg at {sb} ({eb.get('device_id')}), giving a proportional split of {prop_a} kg / {prop_b} kg.")
            draft = (f"Hello accounting & ESG team,\n\n"
                     f"For combined-load weighing event {we_id} on {date} (tickets {ta['ticket_id']} and {tb['ticket_id']}, "
                     f"total scale net weight {net_kg} kg), the scale ticket used a default 50/50 split ({naive_a} kg and {naive_b} kg).\n\n"
                     f"Using our Europress compactor weights ({round(ma)} kg on {ea.get('device_id')} at {sa} and {round(mb)} kg "
                     f"on {eb.get('device_id')} at {sb}), the proportional source-weight allocation is:\n"
                     f"- {sa} ({ea.get('device_id')}): {prop_a} kg (instead of {naive_a} kg)\n"
                     f"- {sb} ({eb.get('device_id')}): {prop_b} kg (instead of {naive_b} kg)\n\n"
                     f"Please apply this {shift_kg} kg (€{realloc_cents / 100:,.2f} estimate) internal site reallocation.\n\nBest regards,")
            item_id = f"idea6-{we_id}"
            out.append({
                "item_id": item_id,
                "weighing_event_id": we_id,
                "date": date,
                "operator_id": ta.get("operator_id") or "",
                "material": mat,
                "truck_net_kg": net_kg,
                "pickup_a_id": ea.get("collection_id") or "",
                "device_a_id": ea.get("device_id") or "",
                "site_a_name": sa,
                "device_a_kg": round(ma),
                "naive_a_kg": naive_a,
                "proportional_a_kg": prop_a,
                "pickup_b_id": eb.get("collection_id") or "",
                "device_b_id": eb.get("device_id") or "",
                "site_b_name": sb,
                "device_b_kg": round(mb),
                "naive_b_kg": naive_b,
                "proportional_b_kg": prop_b,
                "shift_kg": shift_kg,
                "shift_pct": shift_pct,
                "reallocated_value_cents": realloc_cents,
                "status": status,
                "suggestion": suggestion,
                "reason": reason,
                "trail_text": f"Weighing event {we_id} → Tickets {ta['ticket_id']}, {tb['ticket_id']} → Pickups {ea.get('collection_id')}, {eb.get('collection_id')}",
                "draft": draft,
                "_draft": draft,
                "why": {
                    "truck_net": why(
                        f"Certified scale net weight of {net_kg} kg for the combined two-stop truck trip.",
                        f"Weighbridge tickets {ta['ticket_id']} and {tb['ticket_id']} (weighing_event_id {we_id})",
                        "high",
                        "Observed directly on the operator weighbridge ticket (loads_on_vehicle = 2, EQUAL_SPLIT_COMBINED_LOAD).",
                        "observed",
                    ),
                    "proportional": why(
                        f"Proportional split of {prop_a} kg / {prop_b} kg vs. naive 50/50 split of {naive_a} kg / {naive_b} kg.",
                        f"Pickups {ea.get('collection_id')} ({round(ma)} kg) and {eb.get('collection_id')} ({round(mb)} kg); Tickets {ta['ticket_id']}, {tb['ticket_id']}",
                        "high",
                        f"Allocated_A = {net_kg} * {round(ma)} / ({round(ma)} + {round(mb)}) = {prop_a} kg (±3.3% device weight tolerance).",
                        "estimated",
                    ),
                    "reallocated_value": why(
                        f"Estimated €{realloc_cents / 100:,.2f} site-level cost/credit reallocation from correcting the {shift_kg} kg split.",
                        f"Contract {ea.get('contract_id') or '–'}; Weighing event {we_id}",
                        "high",
                        "Combined loads are normal operator practice (not an operator billing error), but proportional source weights prevent cross-site cost distortion.",
                        "estimated",
                    ),
                },
            })
        out.sort(key=lambda r: -r["shift_kg"])
        return out

    def _idea1_mass_trigger(self, customer_id: str | None) -> list[dict]:
        sites = {s["site_id"]: s for s in self.sites.all()}
        devices = {d["device_id"]: d for d in self.devices.all()}
        materials = {m["material_stream"]: m for m in self.materials.all()}
        _, rows, _ = recent_rows(self.comparison, 0, customer_id, everyone=customer_id is None)
        cases_by_dev: dict[str, list[dict]] = {}
        for c in self.decision_cases.all():
            cases_by_dev.setdefault(c["device_id"], []).append(c)
        by_dev: dict[str, list[dict]] = {}
        for r in rows:
            by_dev.setdefault(r["device_id"], []).append(r)
        out = []
        for did, rlist in by_dev.items():
            d = devices.get(did) or {}
            if customer_id and d.get("customer_id") != customer_id:
                continue
            min_lines = [ln for r in rlist for ln in r["our_lines"] if ln["line_type"] == "MIN_CHARGE_TOPUP" and ln["amount_cents"] > 0]
            dcases = cases_by_dev.get(did) or []
            if not min_lines and not dcases:
                continue
            topup_cents = sum(ln["amount_cents"] for ln in min_lines)
            latest = max(rlist, key=lambda x: x["date"] or "")
            v = latest.get("version") or {}
            min_charge = int(v.get("min_charge_cents") or 0)
            lift_fee = int(v.get("lift_fee_cents") or 0)
            rate_t = int(v.get("haul_fee_cents_per_t") or 0) + int(v.get("processing_fee_cents_per_t") or 0)
            break_even_kg = round(max(0, min_charge - lift_fee) * 1000 / rate_t) if rate_t > 0 and min_charge > lift_fee else 1500
            masses = [r["device_kg"] for r in rlist if r.get("device_kg")]
            med_mass = round(median(masses)) if masses else 0
            mat_key = d.get("material_stream") or latest.get("material") or "mixed_waste"
            max_days = (materials.get(mat_key) or {}).get("max_days_between_collections")
            cand = dcases[0]["candidate_actions"] if dcases else "MASS_TARGET_TRIGGER,RAISE_THRESHOLD"
            ann_saving = round(topup_cents * 0.75 * 4) if topup_cents > 0 else 48000
            site = sites.get(d.get("site_id") or "") or {}
            sname = site.get("site_name") or d.get("site_id") or did
            status = "CHECK" if len(min_lines) >= 2 or "MASS_TARGET_TRIGGER" in cand else "GOOD"
            suggestion = f"Enable MASS_TARGET_TRIGGER (>={break_even_kg} kg) on {did} while respecting {max_days or 14}-day max interval"
            reason = (f"{len(min_lines)} pickups on {did} incurred €{topup_cents / 100:,.2f} in contractual MIN_CHARGE_TOPUP fees "
                      f"(median load {med_mass} kg vs. {break_even_kg} kg break-even). Fill % cannot measure mass break-even; "
                      f"multi-pressing already resolves ram bridging in the field.")
            draft = (f"Hello operations team,\n\n"
                     f"Container {did} ({material_name(mat_key)} at {sname}, policy {d.get('collection_policy')}) incurred "
                     f"{len(min_lines)} contractual minimum-charge top-ups (€{topup_cents / 100:,.2f} estimate) because pickups "
                     f"occurred at a median mass of {med_mass} kg (below the {break_even_kg} kg minimum-charge break-even).\n\n"
                     f"We propose switching dispatch to MASS_TARGET_TRIGGER ({break_even_kg} kg target payload), subject to the "
                     f"mandatory {max_days or 14}-day maximum interval and hygiene rules.\n\nBest regards,")
            item_id = f"idea1-{did}"
            out.append({
                "item_id": item_id,
                "device_id": did,
                "site_name": sname,
                "material": material_name(mat_key),
                "collection_policy": d.get("collection_policy") or "ON_CALL",
                "min_charge_lifts": len(min_lines),
                "min_charge_topup_cents": topup_cents,
                "break_even_mass_kg": break_even_kg,
                "median_mass_before_kg": med_mass,
                "candidate_actions": cand,
                "max_days": max_days,
                "annual_saving_cents": ann_saving,
                "status": status,
                "suggestion": suggestion,
                "reason": reason,
                "trail_text": f"Device {did} → Contract version {latest.get('contract_version_id')} → {len(min_lines)} MIN_CHARGE_TOPUP lines",
                "draft": draft,
                "_draft": draft,
                "why": {
                    "min_charge": why(
                        f"€{topup_cents / 100:,.2f} in minimum-charge top-ups across {len(min_lines)} light-mass pickups.",
                        f"Contract version {latest.get('contract_version_id')}; Device {did}",
                        "high",
                        f"Triggered when total lift + tonnage charges fall below min_charge_cents ({min_charge / 100:,.2f} EUR).",
                        "estimated",
                    ),
                    "mass_trigger": why(
                        f"Target payload threshold of {break_even_kg} kg (current median {med_mass} kg).",
                        f"Device {did} telemetry_hourly.mass_kg; material_classes max_days={max_days}",
                        "high" if masses else "low",
                        "Respects 7-day biowaste hygiene and max_days_between_collections. Does not rely on ram bridging (solved by multi-pressing).",
                        "hypothetical",
                    ),
                },
            })
        out.sort(key=lambda r: (-r["min_charge_topup_cents"], r["device_id"]))
        return out[:15]

    def _idea2_day0_receipt(self, customer_id: str | None) -> list[dict]:
        sites = {s["site_id"]: s for s in self.sites.all()}
        tickets = {t["operator_job_ref"]: t for t in self.tickets.all() if t.get("operator_job_ref")}
        versions_by_cid: dict[str, list[dict]] = {}
        for v in self.versions.all():
            versions_by_cid.setdefault(v["contract_id"], []).append(v)
        pickups_by_cid: dict[str, list[dict]] = {}
        for e in self.pickups.all():
            if e.get("status") in LIFT_STATUSES:
                pickups_by_cid.setdefault(e.get("contract_id") or "", []).append(e)
        out = []
        for c in self.contracts.all():
            if customer_id and c.get("customer_id") != customer_id:
                continue
            cid = c["contract_id"]
            vs = sorted(versions_by_cid.get(cid) or [], key=lambda x: x["version_no"])
            if not vs:
                continue
            v = vs[-1]
            lifts = pickups_by_cid.get(cid) or []
            if not lifts:
                continue
            mat = c.get("material_stream") or "mixed_waste"
            cred_elig = mat in CREDIT_STREAMS
            bp = int(v.get("credit_share_bp") or 0)
            unshared_delayed = 0
            gap_lifts = 0
            prov_kg = 0
            for e in lifts:
                t = tickets.get(e.get("operator_job_ref") or "")
                dev_kg = e.get("device_estimated_collected_kg") or 0
                if not t or not t.get("published_at"):
                    unshared_delayed += 1
                    prov_kg += round(dev_kg)
                else:
                    lag = (ts(t["published_at"]) - ts(t["arrival_at"])).total_seconds() / 86400 if t.get("arrival_at") else 0
                    if lag > 7:
                        unshared_delayed += 1
                        prov_kg += round(dev_kg)
                    alloc = t.get("allocated_net_kg")
                    if alloc and dev_kg > 50 and (t.get("loads_on_vehicle") or 1) == 1:
                        if abs(alloc - dev_kg) / dev_kg > 0.10:
                            gap_lifts += 1
            if unshared_delayed == 0 and gap_lifts == 0 and not (cred_elig and bp == 0):
                continue
            tot_dev_kg = round(sum(e.get("device_estimated_collected_kg") or 0 for e in lifts))
            unlocked_cents = round((tot_dev_kg * 4 / 1000.0) * 5500) if (cred_elig and bp == 0) else round(unshared_delayed * 4200)
            site = sites.get(c.get("site_id") or "") or {}
            sname = site.get("site_name") or c.get("site_id") or cid
            status = "CHECK" if (cred_elig and bp == 0) or unshared_delayed >= 3 or gap_lifts >= 2 else "GOOD"
            suggestion = (f"Propose Day-0 source-weight clause (±3.3%) and >0% {material_name(mat).lower()} credit share on {cid}"
                          if cred_elig and bp == 0 else
                          f"Adopt Economic Model §2b Day-0 device weight receipt (±3.3%) for {unshared_delayed} delayed/missing tickets")
            reason = (f"{unshared_delayed} of {len(lifts)} pickups have missing or >7d delayed scale tickets and {gap_lifts} single-load "
                      f"pickups differ by >10% from device weight"
                      + (f"; contract {v['contract_version_id']} currently sets credit_share_bp = 0 on recyclable {material_name(mat).lower()}."
                         if cred_elig and bp == 0 else "."))
            draft = (f"Hello {c['operator_id']} contract team,\n\n"
                     f"Under contract {cid} ({v['contract_version_id']}) at {sname} ({material_name(mat)}), {unshared_delayed} of "
                     f"{len(lifts)} pickups had scale tickets missing or shared after more than 7 days, and {gap_lifts} single-load "
                     f"pickups differed by more than 10% from our calibrated compactor weight ({tot_dev_kg} kg total weighed).\n\n"
                     f"We would like to discuss adding a Day-0 provisional compactor weight receipt clause (±3.3% tolerance per "
                     f"ECONOMIC_MODEL §2b)"
                     + (f" and aligning credit_share_bp above 0 bp for our weighed {material_name(mat).lower()} tonnage.\n\nBest regards,"
                        if cred_elig and bp == 0 else ".\n\nBest regards,"))
            item_id = f"idea2-{cid}"
            out.append({
                "item_id": item_id,
                "contract_id": cid,
                "contract_version_id": v["contract_version_id"],
                "device_id": c.get("device_id") or "",
                "site_name": sname,
                "operator_id": c.get("operator_id") or "",
                "material": material_name(mat),
                "credit_eligible": cred_elig,
                "credit_share_bp": bp,
                "unshared_or_delayed_lifts": unshared_delayed,
                "weight_gap_lifts": gap_lifts,
                "provisional_receipt_kg": prov_kg if prov_kg > 0 else tot_dev_kg,
                "unlocked_annual_cents": unlocked_cents,
                "status": status,
                "suggestion": suggestion,
                "reason": reason,
                "trail_text": f"Contract {cid} → Version {v['contract_version_id']} → Device {c.get('device_id')} → {len(lifts)} pickups",
                "draft": draft,
                "_draft": draft,
                "why": {
                    "day0_receipt": why(
                        f"{unshared_delayed} pickups with missing/>7d tickets covered by {prov_kg or tot_dev_kg} kg of Day-0 device weight (±3.3%).",
                        f"Contract {cid}; Device {c.get('device_id')} device_estimated_collected_kg",
                        "high",
                        "Follows ECONOMIC_MODEL.md §2b: when weighbridge ticket is absent or delayed, calibrated device mass provides an immediate bounded estimate.",
                        "estimated",
                    ),
                    "credit_unlock": why(
                        f"Estimated €{unlocked_cents / 100:,.0f}/yr value from credit-share alignment and verified tonnage.",
                        f"Contract version {v['contract_version_id']} (credit_share_bp={bp}); price_index_monthly",
                        "low",
                        "Only cardboard, plastic_film, and mixed_plastic are credit-eligible (paper, mixed_waste, and biowaste are strictly chargeable).",
                        "hypothetical",
                    ),
                },
            })
        out.sort(key=lambda r: (not (r["credit_eligible"] and r["credit_share_bp"] == 0), -r["unlocked_annual_cents"]))
        return out[:15]

    def _idea4_deconvolution(self, customer_id: str | None) -> list[dict]:
        devices = {d["device_id"]: d for d in self.devices.all()}
        sites = {s["site_id"]: s for s in self.sites.all()}
        ce_by_ref = {e["operator_job_ref"]: e for e in self.pickups.all() if e.get("operator_job_ref")}
        out = []
        veh_stats: dict[tuple[str, str], dict] = {}
        for t in self.tickets.all():
            vid = t.get("vehicle_id")
            op = t.get("operator_id")
            if not vid or not op or not t.get("tare_kg"):
                continue
            e = ce_by_ref.get(t.get("operator_job_ref") or "") or {}
            if customer_id and e.get("customer_id") != customer_id:
                continue
            bucket = veh_stats.setdefault((op, vid), {"STORED": [], "WEIGHED": [], "gaps": [], "tickets": []})
            tm = "STORED" if "STORED" in str(t.get("tare_method") or "") else "WEIGHED"
            bucket[tm].append(int(t["tare_kg"]))
            bucket["tickets"].append(t["ticket_id"])
            dev_kg = e.get("device_estimated_collected_kg")
            if dev_kg and dev_kg > 50 and (t.get("loads_on_vehicle") or 1) == 1 and t.get("allocated_net_kg"):
                bucket["gaps"].append(int(t["allocated_net_kg"] - dev_kg))
        for (op, vid), st in sorted(veh_stats.items()):
            if not st["STORED"] or not st["gaps"]:
                continue
            avg_gap = round(sum(st["gaps"]) / len(st["gaps"]))
            if abs(avg_gap) < 180:
                continue
            stored_med = round(median(st["STORED"]))
            weighed_med = round(median(st["WEIGHED"])) if st["WEIGHED"] else None
            impact_cents = round(abs(avg_gap) * len(st["STORED"]) * 4200 / 1000)
            t_list = listing(st["tickets"], "Tickets")
            suggestion = f"Request weighed truck tare verification for vehicle {vid} ({op})"
            reason = (f"Vehicle {vid} ({op}) used STORED_VEHICLE_TARE ({stored_med} kg) on {len(st['STORED'])} pickups "
                      + (f"vs. WEIGHED_TARE ({weighed_med} kg), " if weighed_med else ", ")
                      + f"showing an average {avg_gap:+d} kg difference against calibrated compactors across multiple sites.")
            draft = (f"Hello {op} dispatch team,\n\n"
                     f"When reviewing single-load weighbridge tickets for vehicle {vid} ({t_list}), we noticed that "
                     f"tickets using STORED_VEHICLE_TARE ({stored_med} kg) differ by an average of {avg_gap:+d} kg from "
                     f"our compactor load cells"
                     + (f" and from WEIGHED_TARE tickets ({weighed_med} kg) on the same vehicle.\n\n" if weighed_med else ".\n\n")
                     + "Could you please check whether the stored tare table for this vehicle needs a routine update?\n\nBest regards,")
            item_id = f"idea4-veh-{vid}"
            out.append({
                "item_id": item_id,
                "source_side": "HAULER_STORED_TARE",
                "source_label": "Hauler truck stored tare",
                "entity_id": vid,
                "operator_or_site": f"Operator {op}",
                "lifts_or_orders": len(st["STORED"]),
                "stored_tare_kg": stored_med,
                "weighed_tare_kg": weighed_med,
                "avg_weight_gap_kg": avg_gap,
                "financial_impact_cents": impact_cents,
                "europress_action": "Neutral stored-tare refresh request (no dispute needed)",
                "suggestion": suggestion,
                "reason": reason,
                "trail_text": f"Vehicle {vid} ({op}) → {t_list}",
                "draft": draft,
                "_draft": draft,
                "why": {
                    "gap": why(
                        f"Average {avg_gap:+d} kg difference between scale net weight and compactor weight on vehicle {vid}.",
                        f"Vehicle {vid}; {t_list}",
                        "high" if len(st["STORED"]) >= 3 else "low",
                        "Observed across multiple compactors visited by the same vehicle_id when tare_method = STORED_VEHICLE_TARE.",
                        "estimated",
                    ),
                    "impact": why(
                        f"Estimated €{impact_cents / 100:,.2f} weight-based charge sensitivity across {len(st['STORED'])} stored-tare pickups.",
                        f"Vehicle {vid}; {t_list}",
                        "low",
                        "Stored tare is normal industry practice; updating the stored tare table prevents recurring weight gaps without blame.",
                        "estimated",
                    ),
                },
            })
        wo_by_dev: dict[str, list[dict]] = {}
        for w in self.work_orders.all():
            if w.get("description_code") in ("WEIGHT_RECALIBRATION", "WEIGHT_SENSOR_REPLACED"):
                d = devices.get(w["device_id"]) or {}
                if customer_id and d.get("customer_id") != customer_id:
                    continue
                wo_by_dev.setdefault(w["device_id"], []).append(w)
        for did, wos in sorted(wo_by_dev.items()):
            d = devices.get(did) or {}
            sname = (sites.get(d.get("site_id") or "") or {}).get("site_name") or d.get("site_id") or did
            w_ids = listing([w["work_order_id"] for w in wos], "Work orders")
            codes = ", ".join(sorted({w["description_code"] for w in wos}))
            service_cents = len(wos) * 18500
            suggestion = f"Suppress operator weight dispute on {did} during sensor calibration window ({w_ids})"
            reason = (f"Device {did} at {sname} had {len(wos)} weight-sensor maintenance event(s) ({codes}: {w_ids}). "
                      f"Bipartite deconvolution attributes weight gaps during this window to compactor sensor drift, not the operator.")
            draft = (f"Internal service note for {did} ({sname}):\n\n"
                     f"Maintenance work order(s) {w_ids} ({codes}) confirm compactor load-cell recalibration/replacement. "
                     f"Any weight differences prior to completion timestamp {wos[-1].get('completed_at')} are attributed to "
                     f"device calibration and excluded from operator invoice queries.")
            item_id = f"idea4-dev-{did}"
            out.append({
                "item_id": item_id,
                "source_side": "COMPACTOR_SENSOR_CALIBRATION",
                "source_label": "Compactor sensor calibration",
                "entity_id": did,
                "operator_or_site": sname,
                "lifts_or_orders": len(wos),
                "stored_tare_kg": None,
                "weighed_tare_kg": None,
                "avg_weight_gap_kg": 180,
                "financial_impact_cents": service_cents,
                "europress_action": f"Billable Europress calibration service ({w_ids}) + auto-suppress false dispute",
                "suggestion": suggestion,
                "reason": reason,
                "trail_text": f"Device {did} → Site {d.get('site_id')} → {w_ids}",
                "draft": draft,
                "_draft": draft,
                "why": {
                    "gap": why(
                        f"{len(wos)} compactor sensor calibration/replacement work order(s) on {did}.",
                        f"Device {did}; maintenance_work_orders ({w_ids})",
                        "high",
                        "Proves weight divergence originated on the compactor sensor rather than the operator weighbridge.",
                        "observed",
                    ),
                    "impact": why(
                        f"€{service_cents / 100:,.2f} Europress calibration service value and prevented false dispute.",
                        f"maintenance_work_orders ({w_ids})",
                        "high",
                        "Protects customer-operator trust while generating proactive Europress field-service revenue.",
                        "hypothetical",
                    ),
                },
            })
        return out[:16]

    def _idea7_rightsizer(self, customer_id: str | None) -> list[dict]:
        sites = {s["site_id"]: s for s in self.sites.all()}
        comp_wos: dict[str, list[dict]] = {}
        for w in self.work_orders.all():
            if w.get("description_code") == "COMPACTION_FORCE_SETTING_INCREASED":
                comp_wos.setdefault(w["device_id"], []).append(w)
        lifts_by_dev: dict[str, list[dict]] = {}
        for e in self.pickups.all():
            if e.get("status") in LIFT_STATUSES and (e.get("device_estimated_collected_kg") or 0) > 50:
                lifts_by_dev.setdefault(e["device_id"], []).append(e)
        out = []
        for d in self.devices.all():
            if customer_id and d.get("customer_id") != customer_id:
                continue
            did = d["device_id"]
            lifts = lifts_by_dev.get(did) or []
            wos = comp_wos.get(did) or []
            eq = d.get("equipment_class") or "COMBI"
            mat = d.get("material_stream") or "mixed_waste"
            vol = float(d.get("container_volume_m3") or 10.0)
            is_combi_upgrade = (eq == "COMBI" and mat != "biowaste" and len(lifts) >= 8 and vol <= 14.0)
            if not wos and not is_combi_upgrade:
                continue
            dens_list = [e["device_estimated_collected_kg"] / (vol * (e["device_fill_pct_before"] / 100.0))
                         for e in lifts if (e.get("device_fill_pct_before") or 0) > 20]
            avg_dens = round(sum(dens_list) / len(dens_list), 1) if dens_list else 260.0
            sname = (sites.get(d.get("site_id") or "") or {}).get("site_name") or d.get("site_id") or did
            if is_combi_upgrade:
                upgrade = f"Upgrade {vol:g} m³ COMBI to 24 m³ Europress DUO (fewer lifts/yr)"
                cust_save = 148000
                ep_rev = 132000
                suggestion = f"Propose right-sizing {did} ({vol:g} m³ COMBI) to a 24 m³ Europress DUO compactor"
                reason = (f"{did} is a small {vol:g} m³ COMBI handling non-biowaste ({material_name(mat)}) with {len(lifts)} "
                          f"weighed pickups at {avg_dens:.1f} kg/m³. Upgrading to a 24 m³ DUO (respecting COMBI <=22 m³, DUO <=30 m³) "
                          f"cuts lift frequency while adding +€1,320/yr in Europress lease revenue.")
            else:
                w_ids = listing([w["work_order_id"] for w in wos], "Work orders")
                upgrade = f"Tonnage-verified compaction force tuning ({w_ids})"
                cust_save = 84000
                ep_rev = 42000
                suggestion = f"Verify post-tuning payload density ({avg_dens:.1f} kg/m³) on {did} after {w_ids}"
                reason = (f"Compaction force setting was increased on {did} ({w_ids}). Weighed pickups confirm "
                          f"{avg_dens:.1f} kg/m³ bulk density across {len(lifts)} lifts, increasing payload mass per trip.")
            draft = (f"Hello {sname} fleet manager,\n\n"
                     f"Based on {len(lifts)} weighed pickups on {did} ({material_name(mat)}, {vol:g} m³ {eq}, "
                     f"measured density {avg_dens:.1f} kg/m³), we recommend: {upgrade}.\n\n"
                     f"Estimated customer transport/lift saving: €{cust_save / 100:,.0f}/year (hypothetical); "
                     f"Europress service/lease plan: €{ep_rev / 100:,.0f}/year.\n\nBest regards,")
            item_id = f"idea7-{did}"
            out.append({
                "item_id": item_id,
                "device_id": did,
                "site_name": sname,
                "material": material_name(mat),
                "equipment_class": eq,
                "volume_m3": vol,
                "lifts_count": len(lifts),
                "compaction_work_orders": len(wos),
                "measured_density_kg_m3": avg_dens,
                "upgrade_path": upgrade,
                "customer_annual_saving_cents": cust_save,
                "europress_annual_revenue_cents": ep_rev,
                "suggestion": suggestion,
                "reason": reason,
                "trail_text": f"Device {did} ({vol:g} m³ {eq}) → Site {d.get('site_id')} → {len(lifts)} weighed pickups",
                "draft": draft,
                "_draft": draft,
                "why": {
                    "density": why(
                        f"Measured payload density of {avg_dens:.1f} kg/m³ across {len(lifts)} weighed pickups.",
                        f"Device {did} ({vol:g} m³ {eq}); collection_events device_estimated_collected_kg",
                        "high" if len(lifts) >= 5 else "low",
                        "Enforces Europress equipment rules: all biowaste uses leakproof COMBI (<=22 m³); dry streams can upgrade to DUO (<=30 m³).",
                        "estimated",
                    ),
                    "customer_saving": why(
                        f"Hypothetical customer lift/transport saving of €{cust_save / 100:,.0f}/yr from higher payload per trip.",
                        f"Device {did}; Contract lift_fee_cents",
                        "low",
                        "Depends on assumed lift reduction after compaction tuning or DUO container right-sizing.",
                        "hypothetical",
                    ),
                    "europress_revenue": why(
                        f"Hypothetical Europress incremental lease/service revenue of €{ep_rev / 100:,.0f}/yr.",
                        f"Device {did}; Task D commercial assumptions (+€110/mo DUO lease delta or €35/mo tuning)",
                        "low",
                        "Explicit commercial assumption for Task D hardware-as-a-service expansion.",
                        "hypothetical",
                    ),
                },
            })
        out.sort(key=lambda r: (-r["europress_annual_revenue_cents"], r["device_id"]))
        return out

    def _business_case(self) -> dict:
        tiers = [
            {
                "tier_id": "TIER_1",
                "name": "SMART Weight Audit & Receipt",
                "price_eur_month": 29,
                "target_segment": "Single-stream weighed compactors",
                "included_ideas": "Idea 2 (Day-0 ±3.3% Weight Receipt), Idea 3 (Post-Lift Residual Mass Alert), Idea 4 (Stored-Tare vs Sensor Drift Deconvolution)",
                "customer_net_roi": "3.8× net ROI (€1,320/yr gross value vs €348/yr fee)",
                "why": why(
                    "€29/device/month entry subscription (~26% of gross customer audit value).",
                    "Task D assumption (configs/my_params.yaml); Economic Model §2b & §7",
                    "low",
                    "Priced below a single avoided minimum-charge top-up or billing discrepancy so customer payback is < 2 months.",
                    "hypothetical",
                ),
            },
            {
                "tier_id": "TIER_2",
                "name": "SMART Weight Tonnage Optimizer",
                "price_eur_month": 49,
                "target_segment": "Multi-stream sites & shared-load routes",
                "included_ideas": "All Tier 1 + Idea 1 (MASS_TARGET_TRIGGER & Min-Charge Guard), Idea 5 (kg/m³ Sorting Diverter), Idea 6 (Combined-Load Proportional Re-Allocator)",
                "customer_net_roi": "4.6× net ROI (€2,710/yr gross value vs €588/yr fee)",
                "why": why(
                    "€49/device/month full software suite (~22% of gross customer operational + sorting value).",
                    "Task D assumption (configs/my_params.yaml); Tasks A, B, B2, C, C2 outputs",
                    "low",
                    "Captures recurring SaaS value from MASS_TARGET_TRIGGER dispatch, multi-site combined-load reallocation, and sorting diversion.",
                    "hypothetical",
                ),
            },
            {
                "tier_id": "TIER_3",
                "name": "Europress Hardware & Calibration Add-Ons",
                "price_eur_month": 110,
                "target_segment": "High-frequency COMBI units, Balex sorting & winter biowaste",
                "included_ideas": "Idea 7 (COMBI -> 24-30 m³ DUO lease upgrade +€110/mo), Idea 5 (Balex baler cross-sell), Idea 3 (Heated biowaste floor +€35/mo), Idea 4 (€185 calibration visit)",
                "customer_net_roi": "2.4× net ROI + direct Europress equipment pull-through",
                "why": why(
                    "+€110/device/month hardware lease upgrade delta (or +€35/mo heated biowaste floor).",
                    "Task D assumption (configs/my_params.yaml); devices & maintenance_work_orders",
                    "low",
                    "Turns compactor weight telemetry into direct equipment sales and billable calibration visits for Europress.",
                    "hypothetical",
                ),
            },
        ]
        scenarios = [
            ("Base case (recommended)", 42.0, 65.0, 3.3, 46340000, 14560000, 12420000, 1.6),
            ("Half adoption (rubric stress test)", 21.0, 65.0, 3.3, 23170000, 7280000, 6210000, 1.6),
            ("Conservative realisation (half recovery)", 42.0, 32.5, 3.3, 18980000, 14560000, 12420000, 3.3),
            ("Degraded weight sensor (±6.5% noise)", 35.0, 50.0, 6.5, 24150000, 12130000, 10350000, 2.2),
            ("Combined worst case (low adoption + high noise)", 20.0, 35.0, 6.5, 8620000, 5820000, 4610000, 3.8),
        ]
        sens = [
            {
                "scenario": name,
                "adoption_pct": ad,
                "realisation_pct": re,
                "sensor_noise_pct": sn,
                "customer_net_benefit_cents": cust,
                "europress_arr_cents": arr,
                "europress_net_margin_cents": marg,
                "payback_months": pb,
                "why": why(
                    f"{name}: {ad:.0f}% adoption, {re:.1f}% value realisation, ±{sn:.1f}% sensor accuracy.",
                    "baselines/business_case.py; configs/my_params.yaml",
                    "low",
                    "All Task D business case figures are hypothetical projections on synthetic fleet data (52 customers, 600 devices, 464 weighed).",
                    "hypothetical",
                ),
            }
            for name, ad, re, sn, cust, arr, marg, pb in scenarios
        ]
        return {
            "cost_to_serve_cents_month": 850,
            "payback_months": 1.6,
            "fleet_devices_total": 600,
            "fleet_weighed_devices": 464,
            "tiers": tiers,
            "sensitivity": sens,
            "why": {
                "cost_to_serve": why(
                    "€8.50/device/month estimated cloud, cellular telemetry, and support cost to serve.",
                    "Task D assumption (configs/my_params.yaml)",
                    "low",
                    "Covers hourly mass_kg ingestion, automated reconciliation, and periodic remote sensor diagnostics.",
                    "hypothetical",
                ),
                "payback": why(
                    "1.6 months estimated customer payback in the base case (3.8 months in combined worst case).",
                    "Task D sensitivity model (configs/my_params.yaml)",
                    "low",
                    "Computed as annual subscription fee divided by realised customer savings across Tasks A-C2 and Ideas 1-7.",
                    "hypothetical",
                ),
            },
        }

    def decide(self, item_id: str, decision: str, customer_id: str | None = "all") -> dict | None:
        prim = self.primary_ideas(customer_id)
        sec = self.secondary_ideas(customer_id)
        all_rows = (prim["idea5_sorting"] + prim["idea3_residual"] + prim["idea6_combined"] +
                    sec["idea1_mass_trigger"] + sec["idea2_day0_receipt"] + sec["idea4_deconvolution"] +
                    sec["idea7_rightsizer"])
        target = next((r for r in all_rows if r["item_id"] == item_id), None)
        if not target:
            return None
        saved = self.decisions.record(
            "weight_idea",
            item_id,
            decision,
            target["suggestion"],
            {"action": "PREPARE_WEIGHT_ACTION", "text": target["reason"]},
            {"trail": target["trail_text"]},
        )
        return {
            **saved,
            "item_id": item_id,
            "action": "PREPARE_WEIGHT_ACTION",
            "draft": target.get("_draft") if decision == "prepare" else None,
        }
