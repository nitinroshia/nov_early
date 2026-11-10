import json
from pathlib import Path

INPUT_FILE = Path("screener_fields.json")
OUTPUT_FILE = Path("screener_fields_report.txt")

if not INPUT_FILE.exists():
    raise FileNotFoundError(f"Missing file: {INPUT_FILE}")

with INPUT_FILE.open("r", encoding="utf-8") as f:
    data = json.load(f)

def inspect(obj, path=""):
    results = []

    if isinstance(obj, dict):
        if any(k in obj for k in ("label", "display", "field", "name")):
            results.append({
                "path": path,
                "label": obj.get("label"),
                "display": obj.get("display"),
                "field": obj.get("field"),
                "name": obj.get("name"),
                "type": obj.get("type"),
                "premium": obj.get("premium"),
            })

        for key, value in obj.items():
            results.extend(inspect(value, f"{path}.{key}"))

    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            results.extend(inspect(value, f"{path}[{i}]"))

    return results

fields = inspect(data)

with OUTPUT_FILE.open("w", encoding="utf-8") as f:
    f.write(f"TOTAL FIELD ENTRIES: {len(fields)}\n\n")

    for index, field in enumerate(fields, 1):
        f.write(f"{index}. {json.dumps(field, ensure_ascii=False)}\n")

print(f"Total field entries: {len(fields)}")
print(f"Report saved to: {OUTPUT_FILE}")
