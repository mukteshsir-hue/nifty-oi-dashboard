import pandas as pd
from nsepython import *
import time
import schedule
from datetime import datetime
import os

DATA_FILE = "data/oi_trend.csv"

def fetch_oi_data():
    print("Fetching data...")
    try:
        symbol = "NIFTY"
        oc = option_chain(symbol)
        ce = oc['filtered']['data'][0]['CE']
        pe = oc['filtered']['data'][0]['PE']

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = {
            "timestamp": now,
            "call_ltp": ce['lastPrice'],
            "call_oi": ce.get('openInterest', 0),
            "put_ltp": pe['lastPrice'],
            "put_oi": pe.get('openInterest', 0),
            "total_oi": ce.get('openInterest', 0) + pe.get('openInterest', 0)
        }

        df_new = pd.DataFrame([data])
        if os.path.exists(DATA_FILE):
            df = pd.read_csv(DATA_FILE)
            df = pd.concat([df, df_new], ignore_index=True)
        else:
            df = df_new

        df.to_csv(DATA_FILE, index=False)
        print("Data logged.")

    except Exception as e:
        print(f"Error: {e}")

schedule.every(1).minutes.do(fetch_oi_data)

if __name__ == "__main__":
    print("Starting data collector...")
    fetch_oi_data()
    while True:
        schedule.run_pending()
        time.sleep(1)
