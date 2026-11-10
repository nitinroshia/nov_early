import requests
import json

url = "https://www.nseindia.com/api/corporates-financial-results"

session = requests.Session()

session.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://www.nseindia.com/"
})

try:
    # Establish NSE session
    session.get("https://www.nseindia.com/", timeout=30)

    # Fetch financial results
    response = session.get(
        url,
        params={
            "index": "equities",
            "period": "Quarterly"
        },
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    # Save complete response as JSON
    with open("nse_financial_results.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("Status:", response.status_code)
    print("Total records:", len(data))
    print("Saved to: nse_financial_results.json")

    if data:
        print("First company:", data[0]["companyName"])
        print("Last company:", data[-1]["companyName"])

except requests.RequestException as e:
    print("NSE request failed:", e)

except (ValueError, KeyError) as e:
    print("Data processing failed:", e)