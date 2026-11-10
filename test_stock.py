from tickertape_api import TickertapeClient
import json

tt = TickertapeClient()

ticker = "RELI"

data = {
    "info": tt.stock_info(ticker),
    "summary": tt.stock_summary(ticker),
    "financials_income": tt.stock_financials(
        ticker, statement="income", period="annual"
    ),
    "financials_balance": tt.stock_financials(
        ticker, statement="balancesheet", period="annual"
    ),
    "financials_cashflow": tt.stock_financials(
        ticker, statement="cashflow", period="annual"
    ),
    "checklists": tt.stock_checklists(ticker),
}

with open(f"{ticker}_data.json", "w") as f:
    json.dump(data, f, indent=2, default=str)

print("Downloaded successfully!")