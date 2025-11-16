import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
import plotly.graph_objects as go

# --- Configuration ---
st.set_page_config(page_title="Nifty 50 OI Dashboard", layout="wide")

# Load refresh interval from user config
default_refresh = 60  # Default 60 seconds
if "refresh_interval" not in st.session_state:
    st.session_state.refresh_interval = default_refresh

# Sidebar for configuration
st.sidebar.header("Settings")
refresh_interval = st.sidebar.selectbox("Auto Refresh Interval", ("1 min", "30 sec"))
if refresh_interval == "30 sec":
    st.session_state.refresh_interval = 30
else:
    st.session_state.refresh_interval = 60

manual_refresh = st.sidebar.button("🔄 Manual Refresh")

# Function to fetch live Nifty Option Chain data from NSE API
@st.cache_data(ttl=30)
def get_option_chain():
    url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    data = response.json()
    return data["records"]["data"], data["records"]["underlyingValue"]

# Auto or manual refresh logic
if manual_refresh:
    st.cache_data.clear()
else:
    time.sleep(st.session_state.refresh_interval)

# Fetch data
option_data, spot_price = get_option_chain()

# Display spot price
st.title("📊 Nifty 50 Option Chain Live Dashboard")
st.subheader(f"🔵 Spot Price: {spot_price}")

# Extract table data with Last Traded Price
rows = []
for entry in option_data:
    strike = entry["strikePrice"]
    call = entry.get("CE", {})
    put = entry.get("PE", {})
    
    rows.append({
        "Strike": strike,
        "Call OI": call.get("openInterest", 0),
        "Call Chg in OI": call.get("changeinOpenInterest", 0),
        "Call Volume": call.get("totalTradedVolume", 0),
        "Call LTP": call.get("lastPrice", 0),
        "Put OI": put.get("openInterest", 0),
        "Put Chg in OI": put.get("changeinOpenInterest", 0),
        "Put Volume": put.get("totalTradedVolume", 0),
        "Put LTP": put.get("lastPrice", 0),
    })

df = pd.DataFrame(rows).drop_duplicates(subset=["Strike"])
df_sorted = df.sort_values("Strike")

# Select 10 rows above and below spot price
closest_index = df_sorted["Strike"].sub(spot_price).abs().idxmin()
start_index = max(0, closest_index - 10)
end_index = closest_index + 10

display_df = df_sorted.iloc[start_index:end_index + 1]

# Add footer row with summation
total_row = {
    "Strike": "TOTAL",
    "Call OI": display_df["Call OI"].sum(),
    "Call Chg in OI": display_df["Call Chg in OI"].sum(),
    "Call Volume": display_df["Call Volume"].sum(),
    "Call LTP": "-",
    "Put OI": display_df["Put OI"].sum(),
    "Put Chg in OI": display_df["Put Chg in OI"].sum(),
    "Put Volume": display_df["Put Volume"].sum(),
    "Put LTP": "-"
}
display_df = display_df.append(total_row, ignore_index=True)

# Highlight the current spot price row
def highlight_spot_row(row):
    if row["Strike"] == spot_price:
        return ["background-color: yellow"] * len(row)
    return [""] * len(row)

st.write("### Strike-wise Option Chain Data")
st.dataframe(display_df.style.apply(highlight_spot_row, axis=1), use_container_width=True)

# Graphical Summary
call_oi_sum = display_df["Call Chg in OI"].iloc[:-1].sum()
put_oi_sum = display_df["Put Chg in OI"].iloc[:-1].sum()

fig = go.Figure(data=[
    go.Bar(name="Call Change in OI", x=["Calls"], y=[call_oi_sum]),
    go.Bar(name="Put Change in OI", x=["Puts"], y=[put_oi_sum])
])

fig.update_layout(title_text="Total Change in OI (Calls vs Puts)", barmode="group")
st.plotly_chart(fig)

# Footer
st.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
