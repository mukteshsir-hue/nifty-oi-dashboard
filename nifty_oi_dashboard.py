import streamlit as st
import requests
import pandas as pd
import numpy as np
import time

# Fetch NIFTY option chain data from NSE
@st.cache_data(ttl=30)
def fetch_option_chain():
    url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        return data["records"]["data"], data["records"]["underlyingValue"]
    except Exception as e:
        st.error(f"Failed to fetch option chain data: {e}")
        return None, None

# Get nearest strike prices around the spot
def get_strike_range(data, spot, rows=10):
    filtered = [item for item in data if "CE" in item and "PE" in item]
    df = pd.DataFrame(filtered)
    df["strikePrice"] = df["strikePrice"].astype(float)
    df = df.drop_duplicates(subset="strikePrice")  # Remove duplicates
    df["distance"] = abs(df["strikePrice"] - spot)
    df = df.sort_values(by="distance")
    range_df = df.iloc[:rows*2+1].sort_values(by="strikePrice").reset_index(drop=True)
    return range_df

# App UI
st.title("🔍 NIFTY Option Chain OI Change Monitor")
refresh_rate = st.sidebar.selectbox("⏱ Refresh Interval", ["30 seconds", "1 minute"], index=1)
refresh_interval = 30 if refresh_rate == "30 seconds" else 60

auto_refresh = st.sidebar.checkbox("Enable Auto Refresh", value=True)
if st.sidebar.button("🔄 Manual Refresh"):
    st.cache_data.clear()

data, spot = fetch_option_chain()

if data:
    st.write(f"**NIFTY Spot Price:** `{spot}`")
    df = get_strike_range(data, spot)

    # Extract call and put change in OI
    df["CE_change_OI"] = df["CE"].apply(lambda x: x.get("changeinOpenInterest", 0))
    df["PE_change_OI"] = df["PE"].apply(lambda x: x.get("changeinOpenInterest", 0))
    
    # Add directional weight scale
    df["Weight"] = np.where(
        df["CE_change_OI"] > df["PE_change_OI"],
        "CALL Heavy",
        np.where(df["CE_change_OI"] < df["PE_change_OI"], "PUT Heavy", "Neutral")
    )
    
    # Highlight spot row
    def highlight_spot(row):
        return ['background-color: yellow' if row['strikePrice'] == spot else '' for _ in row]

    # Calculate summary
    call_sum = df["CE_change_OI"].sum()
    put_sum = df["PE_change_OI"].sum()
    net_oi = call_sum - put_sum
    sentiment = "Bullish" if net_oi > 0 else "Bearish" if net_oi < 0 else "Neutral"
    
    # Add summary row
    summary_row = pd.DataFrame({
        "strikePrice": ["Total"],
        "CE_change_OI": [call_sum],
        "PE_change_OI": [put_sum],
        "Weight": [sentiment],
        "distance": [""]
    })
    display_df = pd.concat([df[["strikePrice", "CE_change_OI", "PE_change_OI", "Weight"]], summary_row], ignore_index=True)
    
    styled_df = display_df.style.apply(highlight_spot, axis=1)
    st.dataframe(styled_df, use_container_width=True)

else:
    st.error("Unable to load option chain data.")

# Auto-refresh logic
if auto_refresh:
    st.experimental_rerun()
