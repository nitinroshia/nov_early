import os
import json
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
ISIN = "INE002A01018"
BASE = "https://api.upstox.com/v2/fundamentals"

if not TOKEN:
    raise SystemExit("ERROR: Access token not found in .env")

OUTPUT = Path("results") / datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Bearer {TOKEN}"
}

ENDPOINTS = [
    ("profile", "profile", {}),
    ("balance_sheet", "balance-sheet",
     {"type": "consolidated", "fs": "true"}),
    ("cash_flow", "cash-flow",
     {"type": "consolidated", "fs": "true"}),
    ("income_statement", "income-statement",
     {"type": "consolidated", "time_period": "yearly", "fs": "true"}),
    ("share_holdings", "share-holdings", {}),
    ("key_ratios", "key-ratios", {}),
    ("corporate_actions", "corporate-actions", {}),
    ("competitors", "competitors", {}),
]

print(f"\nTesting Upstox Fundamentals")
print(f"ISIN: {ISIN}")
print(f"Output: {OUTPUT}\n")

session = requests.Session()
summary = []

for name, endpoint, params in ENDPOINTS:
    url = f"{BASE}/{ISIN}/{endpoint}"

    try:
        response = session.get(
            url,
            headers=HEADERS,
            params=params,
            timeout=30
        )

        try:
            body = response.json()
        except ValueError:
            body = {"raw_response": response.text}

        result = {
            "endpoint": endpoint,
            "url": response.url,
            "http_status": response.status_code,
            "request_params": params,
            "response": body
        }

        filename = OUTPUT / f"{name}.json"
        filename.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        status = "SUCCESS" if response.ok else "FAILED"

        summary.append({
            "endpoint": name,
            "http_status": response.status_code,
            "status": status
        })

        print(f"{status}: {name} (HTTP {response.status_code})")

    except requests.RequestException as error:
        summary.append({
            "endpoint": name,
            "status": "ERROR",
            "error": str(error)
        })
        print(f"ERROR: {name}: {error}")

(OUTPUT / "summary.json").write_text(
    json.dumps(summary, indent=2),
    encoding="utf-8"
)

print(f"\nCompleted: {len(summary)}/8 endpoints")
print(f"Saved responses in: {OUTPUT}")
