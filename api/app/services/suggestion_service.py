from app.core.config import Settings

MEASURES = ("on_time", "missed_visits", "tickets_shared", "lines_to_check", "weight_vs_ours")
VALUE_KEY = {"REQUEST_TICKETS": "REQUEST_WEIGHBRIDGE_DATA", "CORRECT_LINES": "DISPUTE_INVOICE",
             "RENEGOTIATE": "RENEGOTIATE_CONTRACT", "TENDER": "TENDER_OR_SWITCH_OPERATOR"}
TITLE = {"NONE": "No action needed.", "REQUEST_TICKETS": "Ask for the missing scale tickets.",
         "CORRECT_LINES": "Ask to correct the billed lifts.", "RENEGOTIATE": "Consider renegotiating the contract.",
         "TENDER": "Consider asking other operators for offers."}


def pct(x: float | None) -> str:
    return f"{round((x or 0) * 100)} %"


class SuggestionService:
    def __init__(self, settings: Settings):
        self.s = settings

    def facts(self, m: dict) -> dict[str, str]:
        s = self.s
        return {
            "on_time": f"{pct(m['on_time_rate'])} of pickups were within {s.on_time_window_hours:g} hours of the planned time, "
                       f"below {pct(s.on_time_min)}",
            "missed_visits": f"{m['missed_visits']} planned visits were missed, more than {s.missed_visits_max}",
            "tickets_shared": f"only {pct(m['weighbridge_shared_7d_rate'])} of scale tickets were shared within 7 days, "
                              f"below {pct(s.tickets_shared_min)}",
            "lines_to_check": f"{m['lines_to_check']} of {m['invoice_lines']} invoice items differ from your contract",
            "weight_vs_ours": f"billed weights are {m['weight_bias_pct']:+.0f}% from our container scale"
            if m["weight_bias_pct"] is not None else "weights could not be compared",
        }

    def suggest(self, flags: dict[str, str], persistent: list[str], declined_renegotiation: bool,
                values: dict[str, int], m: dict) -> dict:
        facts = self.facts(m)
        months = self.s.pattern_months
        if persistent and declined_renegotiation and values.get("TENDER_OR_SWITCH_OPERATOR", 0) > 0:
            action = "TENDER"
            why = (f"The same pattern has lasted {months} months ({facts[persistent[0]]}) and renegotiating was "
                   f"declined, so other operators' offers are worth comparing.")
        elif persistent and not declined_renegotiation and values.get("RENEGOTIATE_CONTRACT", 0) > 0:
            action = "RENEGOTIATE"
            why = (f"The same pattern has lasted {months} months ({facts[persistent[0]]}) and similar contracts "
                   f"cost at least {self.s.renegotiation_min_gap_pct:g}% less.")
        elif flags["tickets_shared"] == "CHECK":
            action = "REQUEST_TICKETS"
            why = f"{facts['tickets_shared'][0].upper()}{facts['tickets_shared'][1:]}, so invoices cannot be fully checked."
        elif flags["lines_to_check"] == "CHECK" and m["strong_lines"] > 0:
            action = "CORRECT_LINES"
            why = (f"{m['strong_lines']} of {m['invoice_lines']} invoice lines differ from your contract and the "
                   f"scale ticket supports our numbers.")
        else:
            action = "NONE"
            checks = [k for k in MEASURES if flags[k] == "CHECK"]
            why = ("All five measures are in a normal range." if not checks else
                   f"{facts[checks[0]][0].upper()}{facts[checks[0]][1:]}; a contract step is suggested only after "
                   f"{months} months of the same pattern.")
        value = values.get(VALUE_KEY.get(action, ""))
        return {"action": action, "title": TITLE[action], "why": why,
                "value_cents": value if value and value > 0 else None}

    @staticmethod
    def draft(action: str, name: str, m: dict) -> str | None:
        ask = {
            "REQUEST_TICKETS": "Could you please share the weighbridge tickets (gross, tare and net weight) for our pickups, "
                               "ideally within 7 days of each pickup? It would help us check our invoices.",
            "CORRECT_LINES": f"We compared {m['strong_lines']} invoice lines with our contract and the weighbridge tickets, "
                             f"and the amounts differ. Could you please check them with us and send a correction "
                             f"where needed? We may have missed something on our side.",
            "RENEGOTIATE": "We would like to review our contract terms with you. Similar contracts in our area are priced "
                           "differently, and we would like to discuss whether the terms can be aligned.",
            "TENDER": "We are reviewing our waste collection arrangements and plan to ask for offers. We would welcome "
                      "an offer from you as part of this.",
        }.get(action)
        return f"Hello {name},\n\n{ask}\n\nThank you for your help.\n\nBest regards," if ask else None
