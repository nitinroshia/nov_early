import requests
import json

url = "https://www.nseindia.com/api/corporate-announcements"

session = requests.Session()

session.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://www.nseindia.com/"
})

try:
    # Establish NSE session
    session.get("https://www.nseindia.com/", timeout=30)

    # Fetch corporate announcements
    response = session.get(
        url,
        params={"index": "equities"},
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    # Save complete response
    with open(
        "nse_corporate_announcements.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("Status:", response.status_code)
    print("Total records:", len(data))
    print("Saved to: nse_corporate_announcements.json")

    if data:
        print("First company:", data[0].get("sm_name"))
        print("Last company:", data[-1].get("sm_name"))

except requests.RequestException as e:
    print("NSE request failed:", e)

except (ValueError, KeyError, TypeError) as e:
    print("Data processing failed:", e)
