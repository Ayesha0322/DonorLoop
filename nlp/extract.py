"""
DonorLoop - NLP Request Extraction

Extracts structured information from free-text blood requests.

Output fields are designed to match the shared `requests` table:
    raw_text
    blood_type
    units_needed
    hospital
    hospital_latitude
    hospital_longitude
    urgency

This module does NOT handle:
    - donor compatibility
    - donor eligibility
    - distance filtering
    - donor ranking
    - escalation
"""

import re
from typing import Optional

import spacy
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from nlp.urgency_classifier import classify_urgency


# ------------------------------------------------------------
# spaCy model
# ------------------------------------------------------------

nlp = spacy.load("en_core_web_sm")


# ------------------------------------------------------------
# Blood type extraction
# ------------------------------------------------------------

BLOOD_TYPES = {
    "O+",
    "O-",
    "A+",
    "A-",
    "B+",
    "B-",
    "AB+",
    "AB-",
}


def extract_blood_type(text: str) -> Optional[str]:
    """
    Extract a blood type such as O+, A-, AB+, etc.

    Returns:
        Blood type string or None.
    """

    pattern = r"\b(AB|A|B|O)\s*([+-])"

    match = re.search(pattern, text.upper())

    if not match:
        return None

    blood_type = f"{match.group(1)}{match.group(2)}"

    if blood_type in BLOOD_TYPES:
        return blood_type

    return None


# ------------------------------------------------------------
# Units extraction
# ------------------------------------------------------------

def extract_units(text: str) -> Optional[int]:
    """
    Extract the number of blood units requested.

    Examples:
        "2 units of O+ blood" -> 2
        "one unit of A+ blood" -> 1
        "3 bags of blood" -> 3

    Returns:
        Integer number of units or None.
    """

    text_lower = text.lower()

    # Numeric quantities
    numeric_match = re.search(
        r"\b(\d+)\s*(?:units?|bags?|pints?)\b",
        text_lower,
    )

    if numeric_match:
        return int(numeric_match.group(1))

    # Written quantities
    word_numbers = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
    }

    word_pattern = (
        r"\b("
        + "|".join(word_numbers.keys())
        + r")\s*(?:units?|bags?|pints?)\b"
    )

    word_match = re.search(word_pattern, text_lower)

    if word_match:
        return word_numbers[word_match.group(1)]

    return None


# ------------------------------------------------------------
# Hospital extraction
# ------------------------------------------------------------

def extract_hospital(text: str) -> Optional[str]:
    """
    Extract a hospital name from common blood-request wording.

    Examples:
        "at Shifa Hospital Islamabad"
        "at Mayo Hospital Lahore"
        "in Lady Reading Hospital Peshawar"

    Returns:
        Hospital name or None.
    """

    # First use a deterministic regex because hospital names
    # in our synthetic dataset commonly contain "Hospital".
    pattern = r"\b([A-Za-z][A-Za-z\s'-]*Hospital)\b"

    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        return match.group(1).strip(" .,!?")

    # Fallback to spaCy.
    doc = nlp(text)

    for ent in doc.ents:
        if ent.label_ in {"ORG", "FAC"} and "hospital" in ent.text.lower():
            return ent.text.strip(" .,!?")

    return None


# ------------------------------------------------------------
# Location extraction
# ------------------------------------------------------------

LOCATIONS = {
    "Islamabad": (33.6844, 73.0479),
    "Rawalpindi": (33.5651, 73.0169),
    "Lahore": (31.5204, 74.3587),
    "Karachi": (24.8607, 67.0011),
    "Peshawar": (34.0151, 71.5249),
    "Multan": (30.1575, 71.5249),
}


def extract_location(text: str) -> Optional[str]:
    """
    Extract a city/location from the request.

    The known DonorLoop synthetic locations are checked first.
    spaCy is used as a fallback.
    """

    text_lower = text.lower()

    # Check known DonorLoop locations.
    for location in LOCATIONS:
        if re.search(rf"\b{re.escape(location.lower())}\b", text_lower):
            return location

    # spaCy fallback.
    doc = nlp(text)

    for ent in doc.ents:
        if ent.label_ in {"GPE", "LOC"}:
            return ent.text.strip(" .,!?")

    return None


# ------------------------------------------------------------
# Coordinates
# ------------------------------------------------------------

def get_coordinates(location: Optional[str]):
    """
    Convert a known location into latitude/longitude.

    Returns:
        (latitude, longitude) or (None, None)
    """

    if not location:
        return None, None

    # Exact match first.
    if location in LOCATIONS:
        return LOCATIONS[location]

    # Case-insensitive match.
    for city, coordinates in LOCATIONS.items():
        if city.lower() == location.lower():
            return coordinates

    return None, None


# Single shared geocoder instance - Nominatim (OpenStreetMap) is free and
# needs no API key, but does require a descriptive user_agent per its
# usage policy, and is rate-limited (~1 request/sec) - fine for a demo,
# not meant for high-volume production use.
_geolocator = Nominatim(user_agent="donorloop-mvp-demo")


def geocode_hospital(hospital_name: str, city: Optional[str] = None, country_hint: str = "Pakistan"):
    """
    Looks up the SPECIFIC hospital's real location via OpenStreetMap, not
    just its city's center point. Including the city as a hint (when known)
    makes the match far more accurate/less ambiguous - "Jinnah Hospital,
    Lahore, Pakistan" resolves correctly; "Jinnah Hospital, Pakistan" alone
    is more likely to mismatch since several cities have a hospital by that
    name.

    Returns:
        (latitude, longitude) or (None, None) if not found or the geocoding
        service is unreachable (e.g. no internet) - callers should treat
        that the same as "location unknown", not crash.
    """
    if not hospital_name:
        return None, None

    query = f"{hospital_name}, {city}, {country_hint}" if city else f"{hospital_name}, {country_hint}"

    try:
        result = _geolocator.geocode(query, timeout=5)
        if result:
            return result.latitude, result.longitude
    except (GeocoderTimedOut, GeocoderServiceError):
        pass

    return None, None


# ------------------------------------------------------------
# Complete NLP request processing
# ------------------------------------------------------------

def process_request(text: str) -> dict:
    """
    Run the complete DonorLoop NLP pipeline.

    Extracts:
        - blood type
        - units needed
        - hospital
        - location coordinates
        - urgency

    Returns:
        Dictionary compatible with the DonorLoop requests table.
    """

    if not isinstance(text, str) or not text.strip():
        raise ValueError("Request text must be a non-empty string.")

    blood_type = extract_blood_type(text)
    units_needed = extract_units(text)
    hospital = extract_hospital(text)
    location = extract_location(text)

    # Try to pinpoint the SPECIFIC hospital first (uses the city as a hint
    # when we have one, for a more accurate match). Only fall back to the
    # city's fixed center point - which is coarse and identical for every
    # hospital in that city - if the specific lookup fails entirely.
    latitude, longitude = geocode_hospital(hospital, city=location) if hospital else (None, None)

    if latitude is None:
        latitude, longitude = get_coordinates(location)

    urgency = classify_urgency(text)

    return {
        "raw_text": text,
        "blood_type": blood_type,
        "units_needed": units_needed,
        "hospital": hospital or location,
        "hospital_latitude": latitude,
        "hospital_longitude": longitude,
        "urgency": urgency,
    }


# ------------------------------------------------------------
# Backward-compatible extraction function
# ------------------------------------------------------------

def extract_request(text: str) -> dict:
    """
    Extract request information without urgency.

    Kept as a separate function so other modules can use
    extraction independently if needed.
    """

    if not isinstance(text, str) or not text.strip():
        raise ValueError("Request text must be a non-empty string.")

    blood_type = extract_blood_type(text)
    units_needed = extract_units(text)
    hospital = extract_hospital(text)
    location = extract_location(text)

    latitude, longitude = get_coordinates(location)

    return {
        "raw_text": text,
        "blood_type": blood_type,
        "units_needed": units_needed,
        "hospital": hospital or location,
        "hospital_latitude": latitude,
        "hospital_longitude": longitude,
    }


# ------------------------------------------------------------
# Manual test
# ------------------------------------------------------------

if __name__ == "__main__":

    sample_requests = [
        "Urgent! We need 2 units of O+ blood at Shifa Hospital Islamabad for surgery immediately.",
        "A+ blood required at Shifa Hospital Islamabad. One unit is needed today.",
        "We need 3 units of B+ blood at Holy Family Hospital Rawalpindi tomorrow.",
        "Routine requirement: one unit of O- blood at Mayo Hospital Lahore next week.",
        "Emergency! AB+ blood needed immediately at Lady Reading Hospital Peshawar.",
    ]

    print("\nDonorLoop Complete NLP Extraction Test")
    print("=" * 60)

    for number, sample in enumerate(sample_requests, start=1):

        print(f"\nREQUEST {number}")
        print("-" * 60)
        print(sample)

        result = process_request(sample)

        print("\nExtracted information:")

        for key, value in result.items():
            print(f"{key}: {value}")