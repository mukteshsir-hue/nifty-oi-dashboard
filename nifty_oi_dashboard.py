import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Nifty OI Dashboard", layout="wide")

# Title and Configuration
st.title("📊 Nifty Option Chain Open Interest Dashboard")
refresh_interval = st.sidebar.selectbox("Auto-refresh interval (seconds)", [30, 60, 90, 120,150], index=1)
auto_refresh = st.sidebar.checkbox("Enable auto-refresh", value=True)

if st.sidebar.button("Refresh Now"):
    st.rerun()

# NSE API URL
NSE_OPTION_CHAIN_API = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"

@st.cache_data(ttl=10)
def fetch_option_chain():
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(NSE_OPTION_CHAIN_API, headers=headers)
    data = response.json()
    return data

# Fetch and process API data
try:
    option_chain_data = fetch_option_chain()
    records = option_chain_data["records"]["data"]
    underlying_value = option_chain_data["records"]["underlyingValue"]
    expiry_dates = option_chain_data["records"]["expiryDates"]
    nearest_expiry = expiry_dates[0] if expiry_dates else None

    st.subheader(f"ℹ️ Nifty Spot Price: **{underlying_value}** | Expiry: **{nearest_expiry}**")

    # Filter by nearest expiry only
    filtered_records = [item for item in records if item.get("expiryDate") == nearest_expiry]

    # Prepare the table data
    table_data = {}
    for record in filtered_records:
        strike = record["strikePrice"]
        call = record.get("CE", {})
        put = record.get("PE", {})

        table_data[strike] = {
            "strikePrice": strike,
            "call_change_oi": call.get("changeinOpenInterest", 0),
            "call_ltp": call.get("lastPrice", 0),
            "put_change_oi": put.get("changeinOpenInterest", 0),
            "put_ltp": put.get("lastPrice", 0),
            "call_put_ltp_sum": call.get("lastPrice", 0) + put.get("lastPrice", 0),
            "weight_diff": call.get("changeinOpenInterest", 0) - put.get("changeinOpenInterest", 0),
        }

    # Limit to 10 above and below spot
    df = pd.DataFrame(table_data.values())
    df = df.sort_values(by="strikePrice")
    df = df[(df["strikePrice"] >= underlying_value - 500) & (df["strikePrice"] <= underlying_value + 500)]

    # Find the nearest strike price to the underlying value
    nearest_strike = df.iloc[(df["strikePrice"] - underlying_value).abs().argmin()]["strikePrice"]

    # Summation row
    sum_row = {
        "strikePrice": "SUM TOTAL",
        "call_change_oi": df["call_change_oi"].sum(),
        "call_ltp": "",
        "put_change_oi": df["put_change_oi"].sum(),
        "put_ltp": "",
        "call_put_ltp_sum": "",
        "weight_diff": df["weight_diff"].sum(),
    }
    df = df._append(sum_row, ignore_index=True)

    # Styling
    def highlight_row(row):
        if row["strikePrice"] == nearest_strike:
            return ["background-color: yellow"] * len(row)
        elif row["strikePrice"] == "SUM TOTAL":
            return ["font-weight: bold"] * len(row)
        else:
            return [""] * len(row)

    styled_df = df.style.apply(highlight_row, axis=1)
    st.dataframe(styled_df, use_container_width=True)

    # Bar chart for change in OI
    totals_df = pd.DataFrame({
        "Side": ["Calls", "Puts"],
        "Change in OI": [sum_row["call_change_oi"], sum_row["put_change_oi"]],
    })
    st.subheader("📊 Total Change in OI Comparison")
    st.bar_chart(totals_df.set_index("Side"))

except Exception as e:
    st.error(f"Failed to retrieve or process data: {e}")

# Auto-refresh logic
if auto_refresh:
    st.rerun()

