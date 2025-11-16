import streamlit as st
import requests
import pandas as pd

# Optional Plotly import
try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

st.set_page_config(page_title="Nifty OI Dashboard", layout="wide")

# Title and Configuration
st.title("📊 Nifty Option Chain Open Interest Dashboard")
refresh_interval = st.sidebar.selectbox("Auto-refresh interval (seconds)", [30, 60], index=1)
auto_refresh = st.sidebar.checkbox("Enable auto-refresh", value=True)
if st.sidebar.button("Refresh Now"):
    st.experimental_rerun()

# NSE API URL for Nifty
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

    st.subheader(f"ℹ️ Nifty Spot Price: **{underlying_value}**")

    # Filter strikes within +/- 10 steps (x50) of the spot price
    strikes = [record["strikePrice"] for record in records]
    unique_strikes = sorted(set(strikes))
    relevant_strikes = [strike for strike in unique_strikes if abs(strike - underlying_value) <= 500]

    table_data = []
    for record in records:
        strike = record["strikePrice"]
        if strike in relevant_strikes:
            call = record.get("CE", {})
            put = record.get("PE", {})

            table_data.append({
                "strikePrice": strike,
                "call_change_oi": call.get("changeinOpenInterest", 0),
                "call_ltp": call.get("lastPrice", 0),
                "put_change_oi": put.get("changeinOpenInterest", 0),
                "put_ltp": put.get("lastPrice", 0),
                "weight_diff": call.get("changeinOpenInterest", 0) - put.get("changeinOpenInterest", 0),
            })

    df = pd.DataFrame(table_data).sort_values(by="strikePrice")

    # Summation row
    sum_row = {
        "strikePrice": "SUM TOTAL",
        "call_change_oi": df["call_change_oi"].sum(),
        "call_ltp": "",
        "put_change_oi": df["put_change_oi"].sum(),
        "put_ltp": "",
        "weight_diff": df["call_change_oi"].sum() - df["put_change_oi"].sum(),
    }

    df = df._append(sum_row, ignore_index=True)

    # Styling - highlight spot price
    def highlight_row(row):
        if row["strikePrice"] == underlying_value:
            return ["background-color: yellow"] * len(row)
        elif row["strikePrice"] == "SUM TOTAL":
            return ["font-weight: bold"] * len(row)
        else:
            return [""] * len(row)

    styled_df = df.style.apply(highlight_row, axis=1)

    # Display the table
    st.dataframe(styled_df, use_container_width=True)

    # Display chart if Plotly is available
    if PLOTLY_AVAILABLE:
        call_sum = sum_row["call_change_oi"]
        put_sum = sum_row["put_change_oi"]
        fig = go.Figure(data=[
            go.Bar(name="Call Change in OI", x=["Calls"], y=[call_sum]),
            go.Bar(name="Put Change in OI", x=["Puts"], y=[put_sum]),
        ])
        fig.update_layout(
            title="📈 Total Change in OI Comparison",
            xaxis_title="Side",
            yaxis_title="Total Change in OI",
        )
        st.plotly_chart(fig)
    else:
        st.warning("Plotly is not installed. No graphical summary shown.")

except Exception as e:
    st.error(f"Failed to retrieve or process data: {e}")

# Auto-refresh logic
if auto_refresh:
    st.experimental_rerun()
