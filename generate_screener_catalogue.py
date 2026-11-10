
import json
from pathlib import Path

INPUT_FILE = Path("screener_fields.json")
JSON_OUTPUT = Path("screener_metrics.json")
MD_OUTPUT = Path("screener_metrics.md")


def extract_fields(data):
    fields = []
    
    def walk(obj, path=""):
        if isinstance(obj, dict):

            # Capture potential field definitions
            if any(k in obj for k in ("label", "display", "field", "name")):
                fields.append({
                    "path": path,
                    "label": obj.get("label"),
                    "display": obj.get("display"),
                    "field": obj.get("field"),
                    "name": obj.get("name"),
                    "type": obj.get("type"),
                    "premium": obj.get("premium"),
                    "definition": obj
                })

            for key, value in obj.items():
                walk(value, f"{path}.{key}")

        elif isinstance(obj, list):
            for i, value in enumerate(obj):
                walk(value, f"{path}[{i}]")

    walk(data)
    return fields


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(INPUT_FILE)

    with INPUT_FILE.open(encoding="utf-8") as f:
        data = json.load(f)

    fields = extract_fields(data)

    # Remove exact duplicate definitions
    unique = {}
    for item in fields:
        key = json.dumps(
            item["definition"],
            sort_keys=True,
            ensure_ascii=False
        )
        unique[key] = item

    fields = list(unique.values())

    # JSON catalogue
    with JSON_OUTPUT.open("w", encoding="utf-8") as f:
        json.dump(fields, f, indent=2, ensure_ascii=False)

    # Markdown catalogue
    with MD_OUTPUT.open("w", encoding="utf-8") as f:
        f.write("# Tickertape Screener Field Catalogue\n\n")
        f.write(f"Total unique definitions: {len(fields)}\n\n")

        f.write("| # | Label | Display | Field | Name | Type | Premium |\n")
        f.write("|---|---|---|---|---|---|---|\n")

        for i, item in enumerate(fields, 1):
            def clean(value):
                if value is None:
                    return "-"
                return str(value).replace("|", "\\|").replace("\n", " ")

            f.write(
                f"| {i} "
                f"| {clean(item['label'])} "
                f"| {clean(item['display'])} "
                f"| {clean(item['field'])} "
                f"| {clean(item['name'])} "
                f"| {clean(item['type'])} "
                f"| {clean(item['premium'])} |\n"
            )

    print("Catalogue generated successfully!")
    print(f"Unique definitions: {len(fields)}")
    print(f"JSON: {JSON_OUTPUT}")
    print(f"Markdown: {MD_OUTPUT}")


if __name__ == "__main__":
    main()
