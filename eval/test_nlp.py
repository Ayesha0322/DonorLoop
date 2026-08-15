import json
import sys
from pathlib import Path


# Find the main DonorLoop folder
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Allow Python to find the nlp folder
sys.path.insert(0, str(PROJECT_ROOT))


# Import Aimen's urgency classifier
from nlp.urgency_classifier import classify_urgency


# Load our demo requests
REQUESTS_FILE = PROJECT_ROOT / "demo" / "sample_requests.json"

with open(REQUESTS_FILE, "r", encoding="utf-8") as file:
    requests = json.load(file)


# Test every request
for request in requests:

    message = request["message"]
    expected = request["expected"]["urgency"]

    predicted = classify_urgency(message)

    print("\nRequest:", request["request_id"])
    print("Message:", message)
    print("Expected:", expected)
    print("Predicted:", predicted)

    if expected == predicted:
        print("Result: CORRECT")
    else:
        print("Result: WRONG")