"""
rules/compatibility.py
Fixed, transparent medical rule for blood-type compatibility - deliberately
NOT a learned model (see proposal section 2.3 / 5, "Core Design Principle").

The canonical compatibility values already live in config.py
(config.COMPATIBILITY) since that's the shared source of truth every module
reads from. This file just exposes a clean, documented function around it
so nlp/, agent/, dashboard/, and eval/ can all call the same thing instead
of reaching into the dict directly.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402


def is_compatible(donor_blood_type: str, recipient_blood_type: str) -> bool:
    """
    Can a donor with donor_blood_type give blood/platelets to someone who
    needs recipient_blood_type?

    Example:
        is_compatible("O-", "A+")  -> True   (O- is the universal donor)
        is_compatible("A+", "O-")  -> False  (A+ can only give to A+/AB+)
    """
    donor_blood_type = donor_blood_type.strip().upper()
    recipient_blood_type = recipient_blood_type.strip().upper()

    if donor_blood_type not in config.COMPATIBILITY:
        raise ValueError(f"Unknown blood type: {donor_blood_type}")
    if recipient_blood_type not in config.COMPATIBILITY:
        raise ValueError(f"Unknown blood type: {recipient_blood_type}")

    return recipient_blood_type in config.COMPATIBILITY[donor_blood_type]


def compatible_donor_types(recipient_blood_type: str) -> list[str]:
    """
    Given what a recipient needs, returns every donor blood type that
    could supply it. Useful for building a single SQL WHERE clause instead
    of filtering donor-by-donor.

    Example:
        compatible_donor_types("O-") -> ["O-"]   (O- can only receive O-)
        compatible_donor_types("AB+") -> [all 8 types] (AB+ is universal recipient)
    """
    recipient_blood_type = recipient_blood_type.strip().upper()
    return [
        donor_type
        for donor_type, can_give_to in config.COMPATIBILITY.items()
        if recipient_blood_type in can_give_to
    ]


if __name__ == "__main__":
    # quick manual check
    print("O- -> A+ :", is_compatible("O-", "A+"))       # True
    print("A+ -> O- :", is_compatible("A+", "O-"))       # False
    print("Who can give to O- patient:", compatible_donor_types("O-"))
    print("Who can give to AB+ patient:", compatible_donor_types("AB+"))
