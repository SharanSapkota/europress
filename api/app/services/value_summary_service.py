from app.services.cards import advanced, bar, card, details, eur, evidence, example, fig, finish, row
from app.services.explain import why
from app.services.feature_data import FeatureData
from app.services.fleet_service import FleetService
from app.services.pickups_service import PickupsService


class ValueSummaryService:
    def __init__(self, data: FeatureData, pickups: PickupsService, fleet: FleetService, params: dict,
                 comparison=None):
        self.comparison = comparison
        self.data = data
        self.pickups = pickups
        self.fleet = fleet
        self.params = params

    def summary(self, customer_id: str | None = "all") -> dict:
        d = self.data.load(customer_id)
        scale = 12 / d["months"]
        devices = len({p["device_id"] for p in d["pickups"]})
        guard = self.pickups.min_charge(customer_id)
        sizing = self.fleet.right_size(customer_id)
        min_charge = sum(c["topup_cents"] for c in guard["could_wait"]) * scale
        right_size = sum(o["saving_cents"] for o in sizing["fits"])
        total = min_charge + right_size
        per_device = total / devices if devices else 0
        p = self.params
        prices = (p.get("pricing") or {}).get("price_per_device_month_eur") or []
        adoption = (p.get("adoption") or {}).get("adoption_share_of_eligible_pct") or []
        costs = p.get("costs") or {}
        operating = float(costs.get("operating_cost_per_device_month_eur") or 0)
        onboarding = float(costs.get("onboarding_per_device_eur") or 0)
        scenarios = []
        for price in prices:
            for share in adoption + ([adoption[-1] / 2] if adoption else []):
                adopted = devices * share / 100
                revenue = adopted * price * 12
                cost = adopted * (operating * 12 + onboarding)
                scenarios.append({"price": price, "adoption_pct": share, "devices": round(adopted, 1),
                                  "revenue_eur": round(revenue), "cost_eur": round(cost), "margin_eur": round(revenue - cost),
                                  "payback_months": round(onboarding / (price - operating), 1) if price > operating else None,
                                  "customer_net_eur": round(per_device / 100 - price * 12)})
        mid = prices[len(prices) // 2] if prices else None
        ex = example(None, None, [
            fig("Devices in scope", devices, tag="OBSERVED"),
            fig("Minimum charges that could be avoided per year", round(min_charge / 100), "€", "ESTIMATED", "scaled estimate"),
            fig("Right-sizing net saving per year", round(right_size / 100), "€", "ESTIMATED", "scaled estimate"),
            fig("Customer value per device per year", round(per_device / 100), "€", "ESTIMATED", "scaled estimate"),
            fig("Package price per device per year", mid * 12 if mid else None, "€", "HYPOTHETICAL"),
        ], [bar("Package price per device per year", (mid or 0) * 12, "€", "HYPOTHETICAL"),
            bar("Customer value per device per year", per_device / 100, "€", "ESTIMATED")],
            f"Customer value is about {eur(per_device)} per device a year (scaled estimate) against a "
            f"{mid * 12 if mid else 0} € package (hypothetical).") if devices else None
        c = card(
            "value.summary", "Value and payback", "What the weight features are worth per device and year.",
            "Good" if per_device and mid and per_device / 100 >= mid * 12 else "Worth a check",
            "This adds up the euro value from the features above and scales it from the months in the data to a year. "
            "Europress package prices and adoption are our own assumptions for the business case. The shared truck "
            "split moves cost between your own sites, so it adds no total saving.",
            ("Fill-only data gives none of these euro figures.",
             f"{eur(total)} a year across {devices} devices (scaled estimate).",
             "A package price can be set below the customer value so both sides gain."),
            ex,
            evidence("ESTIMATED", f"scaled from {d['months']} months; prices and adoption are HYPOTHETICAL",
                     len(guard["topups"]), "The minimum charge guard and right-sizing results above, and our own price, "
                     "cost and adoption assumptions in configs/my_params.yaml.",
                     "Demo data. These figures show the method, not a proven saving."),
            advanced("customer value per device = (avoidable minimum charges × 12 ÷ months + right-sizing net saving) ÷ "
                     "devices; revenue = devices × adoption × price × 12; cost = devices × adoption × (operating × 12 "
                     "+ onboarding)",
                     ["Price €/month", "Adoption %", "Devices", "Revenue €/yr", "Cost €/yr", "Margin €/yr",
                      "Payback months", "Customer net €/device/yr"],
                     [[s["price"], s["adoption_pct"], s["devices"], s["revenue_eur"], s["cost_eur"], s["margin_eur"],
                       s["payback_months"], s["customer_net_eur"]] for s in scenarios]),
            actions=False)
        c["details"] = details(
            f"{devices} devices · {eur(total)} a year (estimate) · {len(scenarios)} price scenarios (hypothetical)",
            "Customer value = avoidable minimum charges scaled to a year plus right-sizing savings. Revenue = devices × "
            "adoption × price × 12; prices and adoption are our assumptions.",
            ["", "Package", "Adoption", "Margin a year"],
            [row(None, f"{s['price']} € a month · {s['adoption_pct']:g}% adoption", s["margin_eur"], "€",
                 s["adoption_pct"], 100, f"{s['devices']:g} devices",
                 f"Customer net {s['customer_net_eur']} € per device", "check" if s["customer_net_eur"] < 0 else "muted")
             for s in scenarios])
        finish(c, f"About {eur(per_device)} of value per device a year (scaled estimate)",
               f"{devices} devices · package {mid * 12 if mid else 0} € a year (hypothetical)", total)
        return {"customer_id": customer_id or "all", "cards": [c], "scenarios": scenarios,
                "value_per_device_cents": round(per_device), "devices": devices}

    def value_page(self, customer_id: str | None = "all") -> dict:
        d = self.data.load(customer_id)
        months, devices = d["months"], len({p["device_id"] for p in d["pickups"]})
        cid = None if customer_id in (None, "all") else customer_id
        invoice = 0
        for period in d["periods"]:
            res = self.comparison.compare(period, cid, cid is None)
            invoice += sum(max(0, x.get("difference_cents", x.get("euros_at_stake_cents", 0)))
                           for x in res["rows"] + res["unmatched_lines"] if x["view"] in ("check", "disputed"))
        topups = sum(t["topup_cents"] for t in self.pickups.min_charge(customer_id)["could_wait"])
        sizing = round(sum(o["saving_cents"] for o in self.fleet.right_size(customer_id)["fits"]) * months / 12)
        found = invoice + topups + sizing
        plans = self.params.get("plans") or {}
        weight = float(plans.get("weight_eur_per_container_month") or 0)
        pro = float(plans.get("pro_eur_per_container_month") or 0)
        cost = round(weight * 100 * devices * months)
        adoption = ((self.params.get("adoption") or {}).get("adoption_share_of_eligible_pct") or [0])[0]
        base = int((self.params.get("market") or {}).get("connected_containers") or 0)
        yearly = round(base * adoption / 100 * weight * 12)
        return {
            "customer_id": customer_id or "all", "months": months, "devices": devices,
            "value_found_cents": found, "plan_cost_cents": cost, "net_cents": found - cost,
            "why": {
                "found": why(f"Value found in the last {months} months (estimate).",
                             f"Invoice differences to check or disputed {eur(invoice)}; minimum charge top-ups that could "
                             f"have waited {eur(topups)}; container size changes {eur(sizing)}", "low",
                             "Estimated from demo data. A difference is not proof of a mistake, so not all of it may be "
                             "returned."),
                "cost": why(f"Weight plan for {devices} containers over {months} months.",
                            f"{weight:g} € per container a month × {devices} containers × {months} months "
                            f"(configs/my_params.yaml)", "high", "Example price, not an offer.", "hypothetical"),
            },
            "plans": [
                {"key": "basic", "name": "Basic", "price_eur": None, "current": False,
                 "features": ["Fill level", "Pickup ordering"]},
                {"key": "weight", "name": "Weight", "price_eur": weight, "current": True,
                 "features": ["Invoice check and disputes", "Cost per tonne", "Pickup rules by weight"]},
                {"key": "pro", "name": "Pro", "price_eur": pro, "current": False,
                 "features": ["Everything in Weight", "Operator scorecard", "Contract and tender advice"]},
            ],
            "europress": {"adoption_pct": adoption, "containers": base, "yearly_eur": yearly,
                          "text": f"If {adoption:g} % of {base} connected containers take the Weight plan"},
        }
