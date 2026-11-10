import requests
import json
import time

BASE_URL = "https://www.nseindia.com/api/corporate-announcements"

SYMBOLS = [
    "GOODYEAR",
    "RELIANCE",
    "TCS",
    "INFY",
    "HDFCBANK",
    "ICICIBANK"
]

LATEST_PER_SYMBOL = 5

session = requests.Session()

session.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://www.nseindia.com/"
})

results = {}

try:
    session.get("https://www.nseindia.com/", timeout=30)

    for symbol in SYMBOLS:

        print(f"Fetching: {symbol}")

        response = session.get(
            BASE_URL,
            params={
                "index": "equities",
                "symbol": symbol
            },
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        # Sort newest first
        data.sort(
            key=lambda x: x.get("sort_date", ""),
            reverse=True
        )

        results[symbol] = data[:LATEST_PER_SYMBOL]

        print("Announcements:", len(results[symbol]))

        time.sleep(1)

    with open(
        "nse_announcements_by_symbol.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\nCompleted!")
    print("Symbols:", len(results))
    print("Saved: nse_announcements_by_symbol.json")

except requests.RequestException as e:
    print("NSE request failed:", e)

except (ValueError, TypeError) as e:
    print("Data processing failed:", e)
