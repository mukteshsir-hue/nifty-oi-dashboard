import requests
import pandas as pd
from datetime import datetime
import time

CSV_FILE = "nifty_oi_data.csv"
FETCH_INTERVAL = 60
NSE_OPTION_CHAIN_URL = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_nse_data():
    response = requests.get(NSE_OPTION_CHAIN_URL, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def process_data(raw_data):
    records = raw_data["records"]["data"]
    timestamp = datetime.now()
    underlying_value = raw_data["records"]["underlyingValue"]
    expiry_dates = raw_data["records"]["expiryDates"]
    nearest_expiry = expiry_dates[0]

    rows = []
    for item in records:
        if item.get("expiryDate") == nearest_expiry:
            strike = item["strikePrice"]
            for side in ["CE", "PE"]:
                option = item.get(side, {})
                rows.append({
                    "timestamp": timestamp,
                    "expiryDate": nearest_expiry,
                    "strikePrice": strike,
                    "side": side,
                    "lastPrice": option.get("lastPrice", 0),
                    "changeInOI": option.get("changeinOpenInterest", 0),
                    "totalOI": option.get("openInterest", 0),
                    "underlyingValue": underlying_value
                })
    return rows

def append_to_csv(rows):
    df = pd.DataFrame(rows)
    header = not pd.io.common.file_exists(CSV_FILE)
    df.to_csv(CSV_FILE, mode='a', header=header, index=False)

if __name__ == "__main__":
    print("Starting Nifty OI Data Collector...")
    while True:
        try:
            raw_data = fetch_nse_data()
            rows = process_data(raw_data)
            append_to_csv(rows)
            print(f"{datetime.now()} - Logged {len(rows)} rows of data.")
        except Exception as e:
            print(f"Error during data fetch: {e}")
        time.sleep(FETCH_INTERVAL)
