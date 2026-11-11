
import json
from pathlib import Path

# Locate the actual JSON in the shared repository
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "records.json"

# Read the JSON
with open(DATA_FILE, "r", encoding="utf-8") as file:
    data = json.load(file)

# Check its structure without printing confidential content
print("JSON type:", type(data).__name__)

if isinstance(data, list):
    print("Number of records:", len(data))

    if data and isinstance(data[0], dict):
        print("Available fields:", list(data[0].keys()))

elif isinstance(data, dict):
    print("Top-level keys:", list(data.keys()))

    for key, value in data.items():
        if isinstance(value, list):
            print("List name:", key)
            print("Number of records:", len(value))

            if value and isinstance(value[0], dict):
                print("Available fields:", list(value[0].keys()))
