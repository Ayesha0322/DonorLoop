"""
agent/orchestrator.py
The "brain" of Module C: filters + ranks donors for a request, then drives
the plan -> act -> observe -> replan loop by calling outreach.py and
escalation.py.

Uses Daniyal's real rules/ functions now that they exist:
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


def run_agent_loop(request_id: int, simulate: bool = True, top_n: int = 5) -> None:
    """
    The autonomous plan -> act -> observe -> replan loop for one request.
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
        print(f"[orchestrator] Contacted {len(contacted)} donor(s) for request {request_id}")

        confirmed = escalation.count_confirmations(request_id, simulate=simulate)

        if confirmed >= units_needed:
            update_request_status(request_id, "resolved")
            print(f"[orchestrator] Request {request_id} resolved ({confirmed}/{units_needed} confirmed)")
            return

        decision = escalation.decide_next_action(escalation_actions_used)
        if decision is None:
            update_request_status(request_id, "escalated")
            print(f"[orchestrator] Request {request_id} exhausted all escalation options "
                  f"({confirmed}/{units_needed} confirmed) - notify a human coordinator.")
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
            print(f"[orchestrator] Blood bank notified for request {request_id}. Ending automated loop.")
            return

        print(f"[orchestrator] Escalating: {action} - {reason}")


if __name__ == "__main__":
    run_agent_loop(request_id=1, simulate=True)