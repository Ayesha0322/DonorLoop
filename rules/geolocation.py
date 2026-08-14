"""
rules/geolocation.py
Distance calculation and radius filtering between a hospital and donors,
using geopy (already in requirements.txt for Module A).
"""

import sys
from pathlib import Path

from geopy.distance import geodesic

sys.path.append(str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in kilometers between two lat/lon points."""
    return geodesic((lat1, lon1), (lat2, lon2)).km


def within_radius(
    hospital_lat: float, hospital_lon: float,
    donor_lat: float, donor_lon: float,
    radius_km: float | None = None,
) -> bool:
    """
    True if a donor is within radius_km of the hospital.
    Defaults to config.DEFAULT_SEARCH_RADIUS_KM if radius_km isn't given.
    """
    radius_km = radius_km if radius_km is not None else config.DEFAULT_SEARCH_RADIUS_KM
    return distance_km(hospital_lat, hospital_lon, donor_lat, donor_lon) <= radius_km


def filter_donors_by_radius(
    donors: list[dict],
    hospital_lat: float, hospital_lon: float,
    radius_km: float | None = None,
) -> list[dict]:
    """
    Given a list of donor dicts (each with 'latitude'/'longitude' keys),
    returns only those within radius_km, each annotated with a
    'distance_km' field, sorted nearest-first.
    """
    radius_km = radius_km if radius_km is not None else config.DEFAULT_SEARCH_RADIUS_KM

    nearby = []
    for donor in donors:
        d = distance_km(hospital_lat, hospital_lon, donor["latitude"], donor["longitude"])
        if d <= radius_km:
            donor_with_distance = dict(donor)
            donor_with_distance["distance_km"] = round(d, 1)
            nearby.append(donor_with_distance)

    nearby.sort(key=lambda d: d["distance_km"])
    return nearby


if __name__ == "__main__":
    # Islamabad hospital, a donor ~5km away in Islamabad, one far away in Karachi
    hospital = (33.6844, 73.0479)
    donors = [
        {"name": "Nearby Donor", "latitude": 33.7000, "longitude": 73.0500},
        {"name": "Far Donor", "latitude": 24.8607, "longitude": 67.0011},
    ]
    result = filter_donors_by_radius(donors, *hospital, radius_km=15)
    print(result)
