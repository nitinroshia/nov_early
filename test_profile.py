import os
import requests
from dotenv import load_dotenv

load_dotenv()

url = "https://api.upstox.com/v2/fundamentals/INE002A01018/profile"

headers = {
    "Accept": "application/json",
    "Authorization": f"Bearer {os.getenv('UPSTOX_ACCESS_TOKEN')}"
}

response = requests.get(url, headers=headers)

print("HTTP Status:", response.status_code)
print(response.text)