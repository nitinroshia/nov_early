
import pandas as pd
import json
from pathlib import Path
from datetime import datetime

# Project root directory
BASE_DIR = Path(__file__).resolve().parent

# Input Excel file
INPUT_FILE = BASE_DIR / "reliance.xlsx"

# Generate unique output filename
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
OUTPUT_FILE = BASE_DIR / f"reliance_{timestamp}.json"

def convert_excel_to_json():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"File not found: {INPUT_FILE}")

    # Read all Excel sheets
    excel_data = pd.read_excel(
        INPUT_FILE,
        sheet_name=None
    )

    result = {}

    for sheet_name, dataframe in excel_data.items():
        # Replace NaN values with None
        dataframe = dataframe.astype(object).where(
            pd.notna(dataframe), None
        )

        result[sheet_name] = dataframe.to_dict(
            orient="records"
        )

    # Save JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            result,
            file,
            indent=4,
            ensure_ascii=False,
            default=str
        )

    print("Conversion completed successfully!")
    print(f"Output file: {OUTPUT_FILE}")


if __name__ == "__main__":
    convert_excel_to_json()
