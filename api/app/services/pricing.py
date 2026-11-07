LIFT_STATUSES = ("COMPLETED", "PARTIAL")
GRADE_QUALITY_BP = {"A": 10000, "B": 8500, "C": 6000, "R": 0}
MASS_LINES = ("HAUL_PER_TONNE", "PROCESSING", "REJECTION_REPROCESSING", "MIN_CHARGE_TOPUP", "MATERIAL_CREDIT")


def rhu(num: int, den: int) -> int:
    sign = -1 if num < 0 else 1
    q, r = divmod(abs(num), den)
    if 2 * r >= den:
        q += 1
    return sign * q


def credit_price_cents_per_t(v: dict, index_cents: int | None, grade: str | None) -> int:
    share = int(v.get("credit_share_bp") or 0)
    if share <= 0 or index_cents is None:
        return 0
    base = max(int(v.get("credit_floor_cents_per_t") or 0), rhu(index_cents * share, 10000))
    return rhu(base * GRADE_QUALITY_BP.get(grade or "A", 10000), 10000)


def price_event(v: dict, status: str, kg: int | None, grade: str | None = None, index_cents: int | None = None,
                emergency: bool = False, side_waste: bool = False, notice_hours: float | None = None,
                credit_eligible: bool = False) -> list[dict]:
    lines: list[dict] = []

    def add(t, qty, unit, rate, amount):
        lines.append({"line_type": t, "quantity": qty, "unit": unit, "rate_cents": rate, "amount_cents": amount})

    if status in LIFT_STATUSES:
        lift = int(v["lift_fee_cents"])
        km = max(0, int(v["contract_km"]) - int(v["free_km"]))
        transport = km * int(v["per_km_cents"])
        remote = int(v["remote_surcharge_cents"])
        if lift:
            add("LIFT_FEE", 1, "lift", lift, lift)
        if transport:
            add("TRANSPORT", km, "km", int(v["per_km_cents"]), transport)
        if remote:
            add("REMOTE_SURCHARGE", 1, "lift", remote, remote)
        base = lift + transport + remote
        fuel = rhu(base * int(v["fuel_surcharge_bp"]), 10000)
        if fuel:
            add("FUEL_SURCHARGE", int(v["fuel_surcharge_bp"]) / 100, "pct_of_base", base, fuel)
        rejected = credit_eligible and grade == "R"
        if kg is not None:
            t = kg / 1000
            haul = rhu(kg * int(v["haul_fee_cents_per_t"]), 1000)
            if haul:
                add("HAUL_PER_TONNE", t, "t", int(v["haul_fee_cents_per_t"]), haul)
            proc = rej = 0
            if rejected:
                rej = rhu(kg * int(v["rejection_fee_cents_per_t"]), 1000)
                if rej:
                    add("REJECTION_REPROCESSING", t, "t", int(v["rejection_fee_cents_per_t"]), rej)
            else:
                proc = rhu(kg * int(v["processing_fee_cents_per_t"]), 1000)
                if proc:
                    add("PROCESSING", t, "t", int(v["processing_fee_cents_per_t"]), proc)
            mn = int(v["min_charge_cents"])
            sub = base + fuel + haul + proc + rej
            if mn and sub < mn:
                add("MIN_CHARGE_TOPUP", 1, "lift", mn - sub, mn - sub)
            if credit_eligible and not rejected:
                cp = credit_price_cents_per_t(v, index_cents, grade)
                if cp:
                    add("MATERIAL_CREDIT", t, "t", -cp, -rhu(kg * cp, 1000))
        if credit_eligible and grade == "C" and int(v["contamination_penalty_cents"]):
            p = int(v["contamination_penalty_cents"])
            add("CONTAMINATION_PENALTY", 1, "lift", p, p)
        if side_waste and int(v["side_waste_fee_cents"]):
            p = int(v["side_waste_fee_cents"])
            add("SIDE_WASTE_FEE", 1, "lift", p, p)
        if emergency and int(v["emergency_surcharge_cents"]):
            p = int(v["emergency_surcharge_cents"])
            add("EMERGENCY_SURCHARGE", 1, "lift", p, p)
    elif status == "CANCELLED_BY_CUSTOMER":
        p = int(v["cancellation_fee_cents"])
        if notice_hours is not None and notice_hours < 24 and p:
            add("CANCELLATION_FEE", 1, "event", p, p)
    elif status == "WASTED_TRIP":
        p = int(v["wasted_trip_fee_cents"])
        if p:
            add("WASTED_TRIP_FEE", 1, "event", p, p)
    return lines


CATEGORY = {
    "LIFT_FEE": "collection", "TRANSPORT": "collection", "REMOTE_SURCHARGE": "collection",
    "FUEL_SURCHARGE": "collection", "HAUL_PER_TONNE": "collection", "MIN_CHARGE_TOPUP": "collection",
    "SIDE_WASTE_FEE": "collection", "EMERGENCY_SURCHARGE": "collection",
    "PROCESSING": "processing", "REJECTION_REPROCESSING": "processing",
    "CONTAMINATION_PENALTY": "penalties", "CANCELLATION_FEE": "penalties", "WASTED_TRIP_FEE": "penalties",
    "MATERIAL_CREDIT": "material_credit",
}


def summarize(lines: list[dict], kg: int | None) -> dict:
    cat = {"collection": 0, "processing": 0, "penalties": 0, "material_credit": 0}
    for ln in lines:
        c = CATEGORY[ln["line_type"]]
        cat[c] += -ln["amount_cents"] if c == "material_credit" else ln["amount_cents"]
    net = cat["material_credit"] - cat["collection"] - cat["processing"] - cat["penalties"]
    known = kg is not None and kg > 0
    return {
        "collection_cost_cents": cat["collection"], "processing_cost_cents": cat["processing"],
        "penalties_cents": cat["penalties"], "material_credit_cents": cat["material_credit"],
        "net_material_contribution_cents": net, "total_customer_cost_cents": -net,
        "collection_cost_cents_per_t": rhu(cat["collection"] * 1000, kg) if known else None,
        "total_cost_cents_per_t": rhu(-net * 1000, kg) if known else None,
    }
