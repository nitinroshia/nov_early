import json

with open("nse_financial_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("Total records:", len(data))
print("\nChecking first 20 records:\n")

for item in data[:20]:
    print("Company:", item.get("companyName"))
    print("Symbol:", item.get("symbol"))
    print("PDF:", item.get("resultDetailedDataLink"))
    print("XBRL:", item.get("xbrl"))
    print("-" * 60)