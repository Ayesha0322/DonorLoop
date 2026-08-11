"""
DonorLoop - Urgency Classifier

Classifies blood requests into:

    critical
    high
    routine

This is a rule-based classifier for the MVP.
It is intentionally simple, explainable, and deterministic.
"""

import re


# ------------------------------------------------------------
# Urgency keywords
# ------------------------------------------------------------

CRITICAL_KEYWORDS = [
    "emergency",
    "emergent",
    "immediately",
    "immediate",
    "critical",
    "life threatening",
    "life-threatening",
    "urgent",
    "urgently",
    "right now",
    "asap",
    "accident",
    "trauma",
    "massive bleeding",
    "severe bleeding",
]

HIGH_KEYWORDS = [
    "today",
    "within hours",
    "this morning",
    "this afternoon",
    "this evening",
    "tonight",
    "soon",
    "surgery today",
    "operation today",
    "needed today",
]

ROUTINE_KEYWORDS = [
    "routine",
    "planned",
    "scheduled",
    "next week",
    "later",
    "elective",
]


def normalize_text(text: str) -> str:
    """
    Normalize request text for keyword matching.
    """

    text = text.lower().strip()

    # Replace repeated whitespace with one space.
    text = re.sub(r"\s+", " ", text)

    return text


def contains_keyword(text: str, keyword: str) -> bool:
    """
    Check whether a keyword/phrase appears in the text.
    """

    # For multi-word phrases, simple substring matching is useful.
    if " " in keyword:
        return keyword in text

    # For individual words, use word boundaries.
    return bool(re.search(rf"\b{re.escape(keyword)}\b", text))


def classify_urgency(text: str) -> str:
    """
    Classify a blood request as critical, high, or routine.

    Priority:
        critical > high > routine

    If no urgency indicators are found, the default is
    'routine'.
    """

    if not isinstance(text, str) or not text.strip():
        raise ValueError("Request text must be a non-empty string.")

    normalized = normalize_text(text)

    # Critical has highest priority.
    for keyword in CRITICAL_KEYWORDS:
        if contains_keyword(normalized, keyword):
            return "critical"

    # Then check high urgency.
    for keyword in HIGH_KEYWORDS:
        if contains_keyword(normalized, keyword):
            return "high"

    # Then routine indicators.
    for keyword in ROUTINE_KEYWORDS:
        if contains_keyword(normalized, keyword):
            return "routine"

    # Default classification.
    return "routine"


# ------------------------------------------------------------
# Manual testing
# ------------------------------------------------------------

if __name__ == "__main__":

    test_requests = [
        "Emergency! AB+ blood is needed immediately.",
        "We need 2 units of O+ blood today for surgery.",
        "Routine requirement: one unit of O- blood needed next week.",
        "A+ blood is required at the hospital.",
    ]

    print("\nDonorLoop Urgency Classifier Test")
    print("-" * 40)

    for request in test_requests:
        urgency = classify_urgency(request)

        print(f"\nRequest: {request}")
        print(f"Urgency: {urgency}")