"""
rules/eligibility.py
Fixed, transparent rule: has enough time passed since a donor's last
donation for them to safely donate again? Deliberately deterministic,
not learned (same reasoning as compatibility.py).

The window length itself lives in config.py (config.ELIGIBILITY_WINDOW_DAYS)
so it's changeable in one place for the whole team.
"""

import sys
from datetime import date, datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402


def is_eligible(last_donation_date: str, as_of: date | None = None) -> bool:
    """
    Returns True if a donor whose last donation was on last_donation_date
    (ISO string 'YYYY-MM-DD') is eligible to donate again as of `as_of`
    (defaults to today).

    Example:
        is_eligible("2026-01-01")  # True if 90+ days have passed
    """
    as_of = as_of or date.today()
    last = datetime.strptime(last_donation_date, "%Y-%m-%d").date()

    if last > as_of:
        raise ValueError(f"last_donation_date {last} is in the future relative to {as_of}")

    return (as_of - last).days >= config.ELIGIBILITY_WINDOW_DAYS


def days_until_eligible(last_donation_date: str, as_of: date | None = None) -> int:
    """
    Returns how many days remain until the donor becomes eligible again.
    Returns 0 if already eligible. Useful for showing "available again in
    X days" on the dashboard.
    """
    as_of = as_of or date.today()
    last = datetime.strptime(last_donation_date, "%Y-%m-%d").date()
    days_since = (as_of - last).days
    remaining = config.ELIGIBILITY_WINDOW_DAYS - days_since
    return max(0, remaining)


if __name__ == "__main__":
    print("Donated 100 days ago, eligible?",
          is_eligible((date.today().replace(day=1)).isoformat()))
    print("Donated today, eligible?", is_eligible(date.today().isoformat()))
    print("Days until eligible (donated today):",
          days_until_eligible(date.today().isoformat()))
