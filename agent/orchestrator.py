"""
agent/orchestrator.py
The "brain" of Module C: filters + ranks donors for a request, then drives
the plan -> act -> observe -> replan loop by calling outreach.py and
escalation.py.

Uses Daniyal's real rules/ functions:
  - rules/compatibility.py -> is_compatible()
  - rules/eligibility.py   -> is_eligible()
  - rules/geolocation.py   -> filter_donors_by_radius()
"""

import sys
from pathlib import Path
from datetime import date, datetime

sys.path.append(str(Path(__file__).resolve().parent.parent))
sys.path.append(str(Path(__file__).resolve().parent))
import config
from db_utils import get_request, get_all_donors, update_request_status
import outreach
import escalation

from rules.compatibility import is_compatible
from rules.eligibility import is_eligible
from rules.geolocation import filter_donors_by_radius


def shortlist_donors(request: dict, radius_km: float, relax_compatibility: bool = False):
    """
    Filters the full donor pool down to eligible, reachable, compatible
    donors for this request, then ranks them.

    Ranking priority (best first):
      1. Exact blood-type match beats a compatible-but-different type
      2. Closer distance
      3. Longer time since last donation (more "rested" donor)
    """
    donors = [dict(d) for d in get_all_donors()]

    filtered = []
    for donor in donors:
        if not is_compatible(donor["blood_type"], request["blood_type"]):
            continue
        if not is_eligible(donor["last_donation_date"]):
            continue
        filtered.append(donor)

    nearby = filter_donors_by_radius(
        filtered,
        request["hospital_latitude"], request["hospital_longitude"],
        radius_km=radius_km,
    )

    for donor in nearby:
        donor["exact_match"] = donor["blood_type"] == request["blood_type"]
        last = datetime.strptime(donor["last_donation_date"], "%Y-%m-%d").date()
        donor["days_since_donation"] = (date.today() - last).days

    nearby.sort(
        key=lambda d: (not d["exact_match"], d["distance_km"], -d["days_since_donation"])
    )
    return nearby


def run_agent_loop_steps(request_id: int, simulate: bool = True, top_n: int = 5):
    """
    Same plan -> act -> observe -> replan loop as run_agent_loop, but as a
    GENERATOR that yields the agent's state after every step instead of
    only returning once at the very end.

    This exists so a UI (like the dashboard's live map) can show the
    search radius actually growing, donors being contacted, and escalation
    reasons appearing one at a time - instead of only seeing the final
    outcome with no visibility into how the agent got there.

    Each yielded dict contains:
        radius_km, relax_compatibility, contacted (list of donor dicts
        with lat/lon/distance), confirmed, units_needed, status
        ("in_progress" | "escalating" | "resolved" | "escalated"),
        and optionally action / reason when an escalation just happened.
    """
    request = get_request(request_id)
    if request is None:
        raise ValueError(f"No request with id {request_id}")
    request = dict(request)

    radius_km = config.DEFAULT_SEARCH_RADIUS_KM
    relax_compatibility = False
    units_needed = request["units_needed"] or config.MIN_CONFIRMATIONS_NEEDED_DEFAULT
    escalation_actions_used = set()

    while True:
        candidates = shortlist_donors(request, radius_km, relax_compatibility)
        contacted = outreach.contact_donors(candidates[:top_n], request)
        confirmed = escalation.count_confirmations(request_id, simulate=simulate)

        base_state = {
            "request": request,
            "radius_km": radius_km,
            "relax_compatibility": relax_compatibility,
            "contacted": contacted,
            "confirmed": confirmed,
            "units_needed": units_needed,
        }

        if confirmed >= units_needed:
            update_request_status(request_id, "resolved")
            yield {**base_state, "status": "resolved"}
            return

        yield {**base_state, "status": "in_progress"}

        decision = escalation.decide_next_action(escalation_actions_used)
        if decision is None:
            update_request_status(request_id, "escalated")
            yield {**base_state, "status": "escalated",
                   "reason": "All escalation options exhausted - notify a human coordinator."}
            return

        action, reason = decision
        escalation.log_escalation(request_id, action, reason)
        escalation_actions_used.add(action)

        if action == "widen_radius":
            radius_km = config.ESCALATED_SEARCH_RADIUS_KM
        elif action == "relax_compatibility":
            relax_compatibility = True
        elif action == "notify_blood_bank":
            update_request_status(request_id, "escalated")
            yield {**base_state, "status": "escalated", "action": action, "reason": reason}
            return

        yield {**base_state, "status": "escalating", "action": action, "reason": reason}


def run_agent_loop(request_id: int, simulate: bool = True, top_n: int = 5) -> None:
    """
    Console-friendly wrapper around run_agent_loop_steps - prints progress
    and runs to completion. Kept for backward compatibility (e.g. running
    `python agent/orchestrator.py` directly).
    """
    for state in run_agent_loop_steps(request_id, simulate=simulate, top_n=top_n):
        print(f"[orchestrator] Contacted {len(state['contacted'])} donor(s) "
              f"for request {request_id} (radius={state['radius_km']}km)")

        if state["status"] == "resolved":
            print(f"[orchestrator] Request {request_id} resolved "
                  f"({state['confirmed']}/{state['units_needed']} confirmed)")
        elif state["status"] == "escalating":
            print(f"[orchestrator] Escalating: {state['action']} - {state['reason']}")
        elif state["status"] == "escalated":
            print(f"[orchestrator] Request {request_id} escalated "
                  f"({state['confirmed']}/{state['units_needed']} confirmed) - {state['reason']}")


if __name__ == "__main__":
    run_agent_loop(request_id=1, simulate=True)
