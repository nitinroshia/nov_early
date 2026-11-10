
import requests
import json
import gzip
from pathlib import Path

URL = "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz"

OUTPUT_FILE = "equity_tickers.json"


def fetch_equity_tickers():
    print("Downloading Upstox instrument master...")

    response = requests.get(URL, timeout=60)
    response.raise_for_status()

    instruments = json.loads(gzip.decompress(response.content))

    equities = [
        item for item in instruments
        if item.get("segment") in ["NSE_EQ", "BSE_EQ"]
        and item.get("instrument_type") == "EQ"
    ]

    equities.sort(
        key=lambda x: (x.get("exchange", ""), x.get("trading_symbol", ""))
    )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(equities, file, indent=2, ensure_ascii=False)

    print(f"Successfully fetched {len(equities)} equity instruments.")
    print(f"Saved to: {Path(OUTPUT_FILE).resolve()}")


if __name__ == "__main__":
    fetch_equity_tickers()
