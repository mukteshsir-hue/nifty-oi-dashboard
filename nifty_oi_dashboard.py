import streamlit as st
import pandas as pd
import altair as alt
import requests
from datetime import datetime

st.set_page_config(page_title="Nifty OI Live Dashboard", layout="wide")
st.title("📊 Nifty Option Chain Live Dashboard")

# Sidebar options
refresh_interval = st.sidebar.selectbox("Auto-refresh interval (seconds)", [30, 60, 120], index=1)
auto_refresh = st.sidebar.checkbox("Enable auto-refresh", value=True)
if st.sidebar.button("Refresh Now"):
    st.experimental_rerun()

NSE_OPTION_CHAIN_API = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
HEADERS = {"User-Agent": "Mozilla/5.0"}

@st.cache_data(ttl=refresh_interval)
def fetch_option_chain():
    response = requests.get(NSE_OPTION_CHAIN_API, headers=HEADERS)
    response.raise_for_status()
    return response.json()

try:
    data = fetch_option_chain()
    records = data["records"]["data"]
    underlying_value = data["records"]["underlyingValue"]
    expiry_dates = data["records"]["expiryDates"]
    nearest_expiry = expiry_dates[0] if expiry_dates else None

    st.subheader(f"ℹ️ Spot Price: **{underlying_value}** | Expiry: **{nearest_expiry}** | Timestamp: {datetime.now().strftime('%H:%M:%S')}")

    # Filter nearest expiry
    filtered_records = [r for r in records if r.get("expiryDate") == nearest_expiry]

    # Prepare DataFrame
    rows = []
    for item in filtered_records:
        strike = item["strikePrice"]
        for side in ["CE", "PE"]:
            option = item.get(side, {})
            rows.append({
                "strikePrice": strike,
                "side": side,
                "lastPrice": option.get("lastPrice", 0),
                "changeInOI": option.get("changeinOpenInterest", 0),
                "totalOI": option.get("openInterest", 0),
                "underlyingValue": underlying_value
            })

    df = pd.DataFrame(rows)

    # Pivot for table
    pivot_df = df.pivot(index="strikePrice", columns="side", values=["changeInOI", "lastPrice"])
    pivot_df.columns = [f"{val} {side}" for val, side in pivot_df.columns]
    pivot_df.reset_index(inplace=True)
    pivot_df["Total LTP"] = pivot_df["lastPrice CE"] + pivot_df["lastPrice PE"]
    pivot_df["Weight Diff (OI)"] = pivot_df["changeInOI CE"] - pivot_df["changeInOI PE"]

    # Highlight nearest strike
    nearest_strike = min(pivot_df["strikePrice"], key=lambda x: abs(x - underlying_value))
    def highlight_row(row):
        return ['background-color: yellow' if row['strikePrice'] == nearest_strike else '' for _ in row]

    # Display table
    st.dataframe(pivot_df.style.apply(highlight_row, axis=1), use_container_width=True, height=600)

    # Summary
    total_call_oi = df[df["side"] == "CE"]["changeInOI"].sum()
    total_put_oi = df[df["side"] == "PE"]["changeInOI"].sum()
    st.markdown(f"""
        <h4>📌 Open Interest Summary:</h4>
        <ul>
            <li><strong>Total Call OI Change:</strong> <span style="color:green;">{total_call_oi:,}</span></li>
            <li><strong>Total Put OI Change:</strong> <span style="color:red;">{total_put_oi:,}</span></li>
        </ul>
        """, unsafe_allow_html=True)

    # Trends tab
    tab1, tab2 = st.tabs(["Table", "Trends by Strike"])
    with tab2:
        st.subheader("📈 Trends by Strike Price")
        strikes = sorted(df["strikePrice"].unique())
        strike = st.selectbox("Select Strike Price", strikes)
        strike_data = df[df["strikePrice"] == strike]

        st.write("### Open Interest Change Trend")
        oi_chart = alt.Chart(strike_data).mark_line().encode(
            x="strikePrice:O", y="changeInOI:Q", color="side:N"
        )
        st.altair_chart(oi_chart, use_container_width=True)

        st.write("### Last Traded Price (LTP) Trend")
        ltp_chart = alt.Chart(strike_data).mark_line().encode(
            x="strikePrice:O", y="lastPrice:Q", color="side:N"
        )
        st.altair_chart(ltp_chart, use_container_width=True)

        st.write("### Total LTP Trend (Call + Put)")
        strike_data["Total_LTP"] = strike_data[strike_data["side"] == "CE"]["lastPrice"].reset_index(drop=True) + strike_data[strike_data["side"] == "PE"]["lastPrice"].reset_index(drop=True)
        total_ltp_chart = alt.Chart(strike_data).mark_line(color="black").encode(
            x="strikePrice:O", y="Total_LTP:Q"
        )
        st.altair_chart(total_ltp_chart, use_container_width=True)

except Exception as e:
    st.error(f"Error fetching NSE data: {e}")

# Auto-refresh
if auto_refresh:
    st.experimental_rerun()
