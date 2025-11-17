import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Nifty OI Dashboard", layout="wide")

# Title and Sidebar
st.title("📊 Nifty Option Chain Open Interest Dashboard")

refresh_interval = st.sidebar.selectbox("Auto-refresh interval (seconds)", [30, 60], index=1)
auto_refresh = st.sidebar.checkbox("Enable auto-refresh", value=True)
if st.sidebar.button("Refresh Now"):
    st.rerun()

# NSE API URL
NSE_OPTION_CHAIN_API = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"

@st.cache_data(ttl=10)
def fetch_option_chain():
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(NSE_OPTION_CHAIN_API, headers=headers)
    response.raise_for_status()
    return response.json()

# Fetch and prepare data
try:
    option_chain = fetch_option_chain()
    records = option_chain["records"]["data"]
    underlying_value = option_chain["records"]["underlyingValue"]
    expiry_dates = option_chain["records"]["expiryDates"]
    nearest_expiry = expiry_dates[0]

    st.subheader(f"ℹ️ Spot Price: **{underlying_value}** | Expiry: **{nearest_expiry}**")

    # Filter records for nearest expiry and build table data
    filtered = [r for r in records if r.get("expiryDate") == nearest_expiry]
    table_data = []
    for row in filtered:
        strike = row["strikePrice"]
        ce = row.get("CE", {})
        pe = row.get("PE", {})

        table_data.append({
            "strikePrice": strike,
            "call_change_oi": ce.get("changeinOpenInterest", 0),
            "call_ltp": ce.get("lastPrice", 0),
            "put_change_oi": pe.get("changeinOpenInterest", 0),
            "put_ltp": pe.get("lastPrice", 0),
            "call_put_ltp_sum": ce.get("lastPrice", 0) + pe.get("lastPrice", 0),
            "weight_diff": ce.get("changeinOpenInterest", 0) - pe.get("changeinOpenInterest", 0)
        })

    df = pd.DataFrame(table_data).sort_values(by="strikePrice")

    # Limit to 10 strikes above and below spot
    df = df[
        (df["strikePrice"] >= underlying_value - 500) &
        (df["strikePrice"] <= underlying_value + 500)
    ]

    # Add summation row
    sum_row = {
        "strikePrice": "TOTAL",
        "call_change_oi": df["call_change_oi"].sum(),
        "call_ltp": "",
        "put_change_oi": df["put_change_oi"].sum(),
        "put_ltp": "",
        "call_put_ltp_sum": "",
        "weight_diff": df["weight_diff"].sum()
    }
    df = df.append(sum_row, ignore_index=True)

    # Highlight current strike and total row
    def highlight_rows(row):
        if row["strikePrice"] == underlying_value:
            return ["background-color: yellow"] * len(row)
        if row["strikePrice"] == "TOTAL":
            return ["font-weight: bold;background-color: #e8e8e8"] * len(row)
        return [""] * len(row)

    # Tabbed layout
    tab1, tab2 = st.tabs(["📋 Strike Summary", "📈 Weight Change Graph"])

    with tab1:
        st.dataframe(
            df.style.apply(highlight_rows, axis=1),
            height=500,
            use_container_width=True
        )

    with tab2:
        chart_df = pd.DataFrame({
            "Side": ["Calls", "Puts"],
            "Change in OI": [
                sum_row["call_change_oi"],
                sum_row["put_change_oi"],
            ]
        })
        st.bar_chart(chart_df.set_index("Side"))

except Exception as e:
    st.error(f"Error: {e}")

# Auto-refresh logic
if auto_refresh:
    st.rerun()
