"""
DonorLoop - NLP Request Extraction

Extracts structured information from free-text blood requests.

Hospital information is resolved from:
    data/processed/hospitals_dataset.csv

Expected hospital dataset columns:
    Hospital Name
    City
    Address
    Latitude
    Longitude

Hospital matching:
    1. Extract hospital phrase from request.
    2. Extract city from request.
    3. Use token-based keyword similarity against the hospital dataset.
    4. Prefer matches containing the requested city.
    5. Use geocoding only as a fallback when the dataset cannot resolve
       the hospital.

This module does NOT handle:
    - donor compatibility
    - donor eligibility
    - distance filtering
    - donor ranking
    - escalation
"""

import re
from pathlib import Path
from typing import Optional

import pandas as pd
import spacy
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from nlp.urgency_classifier import classify_urgency


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

HOSPITAL_DATASET = (
    PROJECT_ROOT / "data" / "processed" / "hospitals_dataset.csv"
)


# ============================================================
# spaCy model
# ============================================================

nlp = spacy.load("en_core_web_sm")


# ============================================================
# Blood types
# ============================================================

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

    Examples:
        O+ blood       -> O+
        AB- blood      -> AB-
        Need 3 O-      -> O-

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


# ============================================================
# Units extraction
# ============================================================

def extract_units(text: str) -> Optional[int]:
    """
    Extract the number of blood units requested.

    Supports:

        "2 units of O+ blood"       -> 2
        "one unit of A+ blood"       -> 1
        "3 bags of blood"            -> 3
        "Need 3 O- blood"            -> 3
        "3 O- units required"       -> 3
        "AB+ blood, 4 units"        -> 4

    Returns:
        Integer number of units or None.
    """

    text_lower = text.lower()

    # --------------------------------------------------------
    # Explicit numeric quantities
    # --------------------------------------------------------

    numeric_match = re.search(
        r"\b(\d+)\s*(?:units?|bags?|pints?)\b",
        text_lower,
    )

    if numeric_match:
        return int(numeric_match.group(1))

    # --------------------------------------------------------
    # Numeric quantity immediately before a blood type.
    #
    # Example:
    #     "Need 3 O- blood"
    # --------------------------------------------------------

    blood_quantity_match = re.search(
        r"\b(\d+)\s+"
        r"(?:"
        r"(?:ab|a|b|o)\s*[+-]"
        r")"
        r"\s*(?:blood|units?|bags?|pints?)?",
        text_lower,
    )

    if blood_quantity_match:
        return int(blood_quantity_match.group(1))

    # --------------------------------------------------------
    # Written quantities
    # --------------------------------------------------------

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

    # Explicit:
    # "three units"
    word_pattern = (
        r"\b("
        + "|".join(word_numbers.keys())
        + r")\s*(?:units?|bags?|pints?)\b"
    )

    word_match = re.search(word_pattern, text_lower)

    if word_match:
        return word_numbers[word_match.group(1)]

    # --------------------------------------------------------
    # Written quantity before blood type:
    #
    # "Need three O- blood"
    # --------------------------------------------------------

    word_blood_match = re.search(
        r"\b("
        + "|".join(word_numbers.keys())
        + r")\s+"
        r"(?:ab|a|b|o)\s*[+-]"
        r"\s*(?:blood|units?|bags?|pints?)?",
        text_lower,
    )

    if word_blood_match:
        return word_numbers[word_blood_match.group(1)]

    return None


# ============================================================
# Load hospital dataset
# ============================================================

def load_hospital_dataset() -> pd.DataFrame:
    """
    Load and validate the hospital dataset.

    Returns:
        Pandas DataFrame containing hospital records.

    Raises:
        FileNotFoundError:
            If the dataset does not exist.

        ValueError:
            If required columns are missing.
    """

    if not HOSPITAL_DATASET.exists():
        raise FileNotFoundError(
            f"Hospital dataset not found: {HOSPITAL_DATASET}"
        )

    df = pd.read_csv(HOSPITAL_DATASET)

    required_columns = {
        "Hospital Name",
        "City",
        "Address",
        "Latitude",
        "Longitude",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            "Hospital dataset is missing required columns: "
            + ", ".join(sorted(missing))
        )

    # Remove records without a hospital name.
    df = df.dropna(subset=["Hospital Name"]).copy()

    # Normalize text columns.
    for column in ["Hospital Name", "City", "Address"]:
        df[column] = df[column].fillna("").astype(str).str.strip()

    # Convert coordinates to numeric values.
    df["Latitude"] = pd.to_numeric(
        df["Latitude"],
        errors="coerce",
    )

    df["Longitude"] = pd.to_numeric(
        df["Longitude"],
        errors="coerce",
    )

    return df


# Load once when the module starts.
HOSPITALS = load_hospital_dataset()


# ============================================================
# Text normalization
# ============================================================

STOP_WORDS = {
    "the",
    "and",
    "of",
    "at",
    "in",
    "on",
    "for",
    "to",
    "a",
    "an",
    "hospital",
    "medical",
    "center",
    "centre",
    "clinic",
    "health",
    "research",
}


def normalize_text(text: str) -> str:
    """
    Normalize text for hospital matching.
    """

    text = str(text).lower()

    # Replace punctuation with spaces.
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    # Collapse repeated whitespace.
    text = re.sub(r"\s+", " ", text).strip()

    return text


def tokenize_for_matching(text: str) -> set[str]:
    """
    Convert text into useful matching tokens.

    Generic words such as 'hospital', 'medical', 'center',
    etc. are removed because they do not help distinguish
    hospitals from one another.
    """

    normalized = normalize_text(text)

    tokens = set(normalized.split())

    return {
        token
        for token in tokens
        if token not in STOP_WORDS
    }


# ============================================================
# City extraction
# ============================================================

def extract_city(text: str) -> Optional[str]:
    """
    Extract a city from the request.

    Uses the hospital dataset itself as the source of known cities.
    The longest city names are checked first.
    spaCy is only used as a fallback.
    """

    text_normalized = normalize_text(text)

    cities = (
        HOSPITALS["City"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    unique_cities = sorted(
        {city for city in cities if city},
        key=len,
        reverse=True,
    )

    # --------------------------------------------------------
    # Dataset-driven city matching
    # --------------------------------------------------------

    for city in unique_cities:
        city_normalized = normalize_text(city)

        if not city_normalized:
            continue

        if re.search(
            rf"\b{re.escape(city_normalized)}\b",
            text_normalized,
        ):
            return city

    # --------------------------------------------------------
    # spaCy fallback
    # --------------------------------------------------------

    doc = nlp(text)

    for ent in doc.ents:
        if ent.label_ in {"GPE", "LOC"}:
            return ent.text.strip(" .,!?")

    return None


# ============================================================
# Hospital phrase extraction
# ============================================================

def extract_hospital_phrase(text: str) -> Optional[str]:
    """
    Extract the hospital phrase from a request.

    Examples:

        "at Shifa Hospital Islamabad"
            -> "Shifa Hospital"

        "at Mayo Hospital Lahore"
            -> "Mayo Hospital"

        "in Mahaban Medical and Research Hospital Topi"
            -> "Mahaban Medical and Research Hospital"

    The function deliberately stops before a recognized city.
    """

    city = extract_city(text)

    working_text = text.strip()

    # --------------------------------------------------------
    # Remove common request prefixes.
    # --------------------------------------------------------

    working_text = re.sub(
        r"^\s*(?:urgent|emergency|critical|routine)\s*[!:,-]?\s*",
        "",
        working_text,
        flags=re.IGNORECASE,
    )

    # --------------------------------------------------------
    # Look for text following:
    #
    # at ...
    # in ...
    # from ...
    # near ...
    # @ ...
    # --------------------------------------------------------

    match = re.search(
        r"\b(?:at|in|from|near)\s+(.+)",
        working_text,
        flags=re.IGNORECASE,
    )

    if match:
        candidate = match.group(1).strip()
    else:
        # Fallback: find a phrase ending in Hospital.
        hospital_match = re.search(
            r"([A-Za-z][A-Za-z\s&'-]*Hospital)",
            working_text,
            flags=re.IGNORECASE,
        )

        if hospital_match:
            candidate = hospital_match.group(1).strip()
        else:
            return None

    # --------------------------------------------------------
    # Remove trailing purpose/time phrases.
    # --------------------------------------------------------

    candidate = re.split(
        r"\b(?:for|because|tomorrow|today|tonight|"
        r"immediately|urgently|urgent|next week|next month)\b",
        candidate,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip()

    # --------------------------------------------------------
    # Remove the city from the end.
    # --------------------------------------------------------

    if city:
        city_pattern = rf"\b{re.escape(city)}\b\s*$"

        candidate = re.sub(
            city_pattern,
            "",
            candidate,
            flags=re.IGNORECASE,
        ).strip(" .,!?")

    # --------------------------------------------------------
    # If the candidate contains "Hospital", keep through the
    # word Hospital and discard anything after it.
    #
    # This prevents:
    #
    # "blood needed immediately at Lady Reading Hospital"
    #
    # from becoming:
    #
    # "blood needed immediately at Lady Reading Hospital"
    # --------------------------------------------------------

    hospital_match = re.search(
        r"([A-Za-z][A-Za-z\s&'-]*Hospital)",
        candidate,
        flags=re.IGNORECASE,
    )

    if hospital_match:
        candidate = hospital_match.group(1).strip()

    # --------------------------------------------------------
    # Clean leading request words accidentally captured.
    # --------------------------------------------------------

    candidate = re.sub(
        r"^(?:blood|bloods|units?|bags?|pints?)\s+",
        "",
        candidate,
        flags=re.IGNORECASE,
    )

    candidate = candidate.strip(" .,!?")

    if not candidate:
        return None

    return candidate


# ============================================================
# Hospital matching
# ============================================================

def hospital_similarity(
    query: str,
    hospital_name: str,
) -> float:
    """
    Calculate token-based keyword similarity.

    Uses Jaccard-style overlap:

        intersection / union

    Generic words such as 'hospital', 'medical', and 'center'
    have already been removed by tokenize_for_matching().
    """

    query_tokens = tokenize_for_matching(query)
    hospital_tokens = tokenize_for_matching(hospital_name)

    if not query_tokens or not hospital_tokens:
        return 0.0

    intersection = query_tokens & hospital_tokens
    union = query_tokens | hospital_tokens

    return len(intersection) / len(union)


def find_hospital(
    hospital_phrase: Optional[str],
    city: Optional[str] = None,
) -> Optional[dict]:
    """
    Find the best hospital in the dataset.

    Matching strategy:

        1. Exact hospital name + city.
        2. Strong token overlap + city.
        3. Token overlap without city.
        4. Reject weak matches rather than returning an
           unrelated hospital.

    Returns:
        Dictionary containing:
            hospital
            hospital_city
            hospital_latitude
            hospital_longitude

        or None.
    """

    if not hospital_phrase:
        return None

    if HOSPITALS.empty:
        return None

    query_normalized = normalize_text(hospital_phrase)

    # --------------------------------------------------------
    # Work on a copy.
    # --------------------------------------------------------

    candidates = HOSPITALS.copy()

    # --------------------------------------------------------
    # City filtering.
    #
    # If the request says "Topi", do NOT allow a hospital
    # from Lahore to win simply because its name has similar
    # words.
    # --------------------------------------------------------

    if city:
        city_normalized = normalize_text(city)

        city_matches = candidates[
            candidates["City"]
            .map(normalize_text)
            .eq(city_normalized)
        ]

        if not city_matches.empty:
            candidates = city_matches

    # --------------------------------------------------------
    # Exact normalized name match.
    # --------------------------------------------------------

    exact = candidates[
        candidates["Hospital Name"]
        .map(normalize_text)
        .eq(query_normalized)
    ]

    if not exact.empty:
        row = exact.iloc[0]

        return {
            "hospital": row["Hospital Name"],
            "hospital_city": row["City"],
            "hospital_latitude": row["Latitude"],
            "hospital_longitude": row["Longitude"],
        }

    # --------------------------------------------------------
    # Token similarity.
    # --------------------------------------------------------

    candidates = candidates.copy()

    candidates["_similarity"] = candidates["Hospital Name"].apply(
        lambda name: hospital_similarity(
            hospital_phrase,
            name,
        )
    )

    candidates = candidates.sort_values(
        "_similarity",
        ascending=False,
    )

    if candidates.empty:
        return None

    best = candidates.iloc[0]
    best_score = float(best["_similarity"])

    # --------------------------------------------------------
    # Require meaningful overlap.
    #
    # This is important:
    #
    # "Lady Reading Hospital Peshawar"
    #
    # must NOT randomly become:
    #
    # "Lady Aitchison Hospital Lahore"
    # --------------------------------------------------------

    if best_score < 0.20:
        return None

    return {
        "hospital": best["Hospital Name"],
        "hospital_city": best["City"],
        "hospital_latitude": best["Latitude"],
        "hospital_longitude": best["Longitude"],
    }


# ============================================================
# Geocoding fallback
# ============================================================

_geolocator = Nominatim(
    user_agent="donorloop-mvp-demo"
)


def geocode_hospital(
    hospital_name: str,
    city: Optional[str] = None,
    country_hint: str = "Pakistan",
):
    """
    Fallback geocoder.

    Normally the hospital dataset should provide the coordinates.
    This is only used if the dataset cannot resolve the hospital.
    """

    if not hospital_name:
        return None, None

    if city:
        query = (
            f"{hospital_name}, "
            f"{city}, "
            f"{country_hint}"
        )
    else:
        query = f"{hospital_name}, {country_hint}"

    try:
        result = _geolocator.geocode(
            query,
            timeout=5,
        )

        if result:
            return result.latitude, result.longitude

    except (
        GeocoderTimedOut,
        GeocoderServiceError,
    ):
        pass

    return None, None


# ============================================================
# Complete request processing
# ============================================================

def process_request(text: str) -> dict:
    """
    Run the complete DonorLoop NLP pipeline.

    Extracts:

        - blood type
        - units needed
        - hospital
        - hospital city
        - hospital latitude
        - hospital longitude
        - urgency

    Returns:
        Dictionary compatible with the DonorLoop requests table,
        with the additional hospital_city field.
    """

    if not isinstance(text, str) or not text.strip():
        raise ValueError(
            "Request text must be a non-empty string."
        )

    # --------------------------------------------------------
    # Basic NLP extraction
    # --------------------------------------------------------

    blood_type = extract_blood_type(text)
    units_needed = extract_units(text)

    # --------------------------------------------------------
    # Hospital and city
    # --------------------------------------------------------

    city = extract_city(text)
    hospital_phrase = extract_hospital_phrase(text)

    # --------------------------------------------------------
    # Dataset matching
    # --------------------------------------------------------

    hospital_match = find_hospital(
        hospital_phrase,
        city=city,
    )

    if hospital_match:
        hospital = hospital_match["hospital"]
        hospital_city = hospital_match["hospital_city"]
        latitude = hospital_match["hospital_latitude"]
        longitude = hospital_match["hospital_longitude"]

    else:
        # ----------------------------------------------------
        # Dataset did not resolve hospital.
        # Try geocoding as a fallback.
        # ----------------------------------------------------

        hospital = hospital_phrase or city
        hospital_city = city

        latitude, longitude = geocode_hospital(
            hospital,
            city=city,
        )

    # --------------------------------------------------------
    # Urgency
    # --------------------------------------------------------

    urgency = classify_urgency(text)

    return {
        "raw_text": text,
        "blood_type": blood_type,
        "units_needed": units_needed,
        "hospital": hospital,
        "hospital_city": hospital_city,
        "hospital_latitude": latitude,
        "hospital_longitude": longitude,
        "urgency": urgency,
    }


# ============================================================
# Backward-compatible extraction function
# ============================================================

def extract_request(text: str) -> dict:
    """
    Backward-compatible extraction function.

    Other modules that only need the original extraction fields
    can continue calling extract_request().
    """

    result = process_request(text)

    return {
        "raw_text": result["raw_text"],
        "blood_type": result["blood_type"],
        "units_needed": result["units_needed"],
        "hospital": result["hospital"],
        "hospital_latitude": result["hospital_latitude"],
        "hospital_longitude": result["hospital_longitude"],
    }


# ============================================================
# Manual tests
# ============================================================

if __name__ == "__main__":

    print("\nDonorLoop Complete NLP Extraction Test")
    print("=" * 70)
    print(f"Hospital dataset: {HOSPITAL_DATASET}")
    print(f"Hospitals loaded: {len(HOSPITALS)}")

    sample_requests = [

        (
            "Urgent! We need 2 units of O+ blood at "
            "Shifa Hospital Islamabad for surgery immediately."
        ),

        (
            "A+ blood required at Shifa Hospital Islamabad. "
            "One unit is needed today."
        ),

        (
            "We need 3 units of B+ blood at "
            "Civil Hospital tomorrow."
        ),

        (
            "Routine requirement: one unit of O- blood at "
            "Mayo Hospital Lahore next week."
        ),

        (
            "Emergency! 2 units of AB+ blood needed immediately "
            "at Liaquat National Hospital."
        ),

        (
            "Need 3 O- blood urgent in "
            "Mahaban Medical and Research Hospital Topi"
        ),
    ]

    for number, sample in enumerate(
        sample_requests,
        start=1,
    ):

        print(f"\nREQUEST {number}")
        print("-" * 70)
        print(sample)

        try:
            result = process_request(sample)

            print("\nExtracted information:")

            for key, value in result.items():
                print(f"{key}: {value}")

        except Exception as exc:
            print(f"\nERROR: {exc}")