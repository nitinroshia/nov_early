from tickertape_api import TickertapeClient
import json

tt = TickertapeClient()

fields = tt.screener_filters()

with open("screener_fields.json", "w") as f:
    json.dump(fields, f, indent=2)