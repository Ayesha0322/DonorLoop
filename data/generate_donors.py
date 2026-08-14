"""
data/generate_donors.py
Generates data/synthetic_donors.csv - a fabricated donor pool for the MVP demo.
No real donor data is used anywhere (see proposal section 14, Ethical Considerations).

Columns match the `donors` table in schema.sql exactly (minus donor_id, which
is auto-assigned when the CSV is loaded into SQLite):
    name, blood_type, city, latitude, longitude, phone, last_donation_date

Run:
    python data/generate_donors.py
Produces:
    data/synthetic_donors.csv  (~200 rows by default)
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

fake = Faker()
Faker.seed(42)   # reproducible dataset across the whole team
random.seed(42)

OUTPUT_PATH = Path(__file__).resolve().parent / "synthetic_donors.csv"
NUM_DONORS = 200

# Same cities + coordinates Aimen's nlp/extract.py already recognizes,
# so requests and donors line up geographically.
CITIES = {
    "Islamabad": (33.6844, 73.0479),
    "Rawalpindi": (33.5651, 73.0169),
    "Lahore": (31.5204, 74.3587),
    "Karachi": (24.8607, 67.0011),
    "Peshawar": (34.0151, 71.5249),
    "Multan": (30.1575, 71.5249),
}

# Roughly realistic population blood-type distribution (rounded, sums to 100).
# Using this instead of a uniform random pick makes the ranking/escalation
# logic (Module C) behave more realistically - O+ and A+ donors are common,
# AB- donors are rare, which is exactly when escalation should kick in.
BLOOD_TYPE_WEIGHTS = {
    "O+": 35, "A+": 30, "B+": 13, "AB+": 5,
    "O-": 7, "A-": 6, "B-": 2, "AB-": 2,
}


def random_blood_type() -> str:
    types = list(BLOOD_TYPE_WEIGHTS.keys())
    weights = list(BLOOD_TYPE_WEIGHTS.values())
    return random.choices(types, weights=weights, k=1)[0]


def jittered_coordinates(lat: float, lon: float) -> tuple[float, float]:
    """Small random offset (~0-6 km) so donors aren't stacked on one point."""
    return (
        round(lat + random.uniform(-0.05, 0.05), 6),
        round(lon + random.uniform(-0.05, 0.05), 6),
    )


def random_phone() -> str:
    """Synthetic Pakistani-style mobile number, clearly fake for the demo."""
    return f"03{random.randint(0, 9)}{random.randint(1000000, 9999999)}"


def random_last_donation_date() -> str:
    """
    Spread donation dates across the last ~10 months so the dataset has a
    realistic mix of eligible (>=90 days ago) and ineligible (<90 days ago)
    donors - important for testing rules/eligibility.py properly.
    """
    days_ago = random.randint(1, 300)
    return (date.today() - timedelta(days=days_ago)).isoformat()


def generate_donors(n: int = NUM_DONORS) -> list[dict]:
    donors = []
    for _ in range(n):
        city, (base_lat, base_lon) = random.choice(list(CITIES.items()))
        lat, lon = jittered_coordinates(base_lat, base_lon)
        donors.append({
            "name": fake.name(),
            "blood_type": random_blood_type(),
            "city": city,
            "latitude": lat,
            "longitude": lon,
            "phone": random_phone(),
            "last_donation_date": random_last_donation_date(),
        })
    return donors


def write_csv(donors: list[dict], path: Path = OUTPUT_PATH) -> None:
    fieldnames = ["name", "blood_type", "city", "latitude", "longitude", "phone", "last_donation_date"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(donors)


if __name__ == "__main__":
    donors = generate_donors()
    write_csv(donors)
    print(f"Wrote {len(donors)} synthetic donors to {OUTPUT_PATH}")

    # quick sanity summary
    from collections import Counter
    bt_counts = Counter(d["blood_type"] for d in donors)
    city_counts = Counter(d["city"] for d in donors)
    print("Blood type breakdown:", dict(bt_counts))
    print("City breakdown:", dict(city_counts))
