import streamlit as st
import requests
import pandas as pd
import altair as alt
import os
from datetime import datetime

# Constants
NSE_OPTION_CHAIN_API = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
DATA_FILE = "nifty_data.csv"

# Page Configuration
st.set_page_config(page_title="Nifty OI & LTP Dashboard", layout="wide")
st.title("📊 Nifty Option Chain Dashboard")

# Sidebar options
refresh_interval = st.sidebar.selectbox("Auto-refresh interval (seconds)", [30, 60], index=1)
enable_auto_refresh = st.sidebar.checkbox("Enable auto-refresh", value=True)

if st.sidebar.button("Refresh Now"):
    st.rerun()

# Function to fetch option chain data
@st.cache_data(ttl=10)
def fetch_option_chain():
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(NSE_OPTION_CHAIN_API, headers=headers)
    data = response.json()
    return data

# Main tabs
tab1, tab2 = st.tabs(["📑 OI Summary", "📈 LTP & OI Trends"])

# --- Tab 1: OI Summary ---
with tab1:
    try:
        option_chain = fetch_option_chain()
        records = option_chain["records"]["data"]
        underlying_value = option_chain["records"]["underlyingValue"]
        expiry_dates = option_chain["records"]["expiryDates"]
        nearest_expiry = expiry_dates[0] if expiry_dates else None
        
        st.subheader(f"ℹ️ Nifty Spot Price: **{underlying_value}** | Expiry: **{nearest_expiry}**")

        # Filter nearest expiry
        filtered_records = [item for item in records if item.get("expiryDate") == nearest_expiry]

        # Build table
        rows = []
        for item in filtered_records:
            strike = item["strikePrice"]
            call = item.get("CE", {})
            put = item.get("PE", {})
            call_oi = call.get("changeinOpenInterest", 0)
            put_oi = put.get("changeinOpenInterest", 0)
            call_ltp = call.get("lastPrice", 0)
            put_ltp = put.get("lastPrice", 0)
            total_ltp = call_ltp + put_ltp

            rows.append({
                "Strike Price": strike,
                "Call Change in OI": call_oi,
                "Put Change in OI": put_oi,
                "Call LTP": call_ltp,
                "Put LTP": put_ltp,
                "Total LTP": total_ltp,
                "Net OI": call_oi - put_oi,
            })

        df = pd.DataFrame(rows)
        df = df.sort_values(by="Strike Price")

        # Highlight nearest strike price
        nearest_strike = df.iloc[(df["Strike Price"] - underlying_value).abs().argsort()[:1]]["Strike Price"].values[0]

        def highlight_row(row):
            return ['background-color: yellow' if row['Strike Price'] == nearest_strike else '' for _ in row]

        st.dataframe(
            df.style.apply(highlight_row, axis=1),
            use_container_width=True, height=600
        )

        # Summary
        total_call_oi = df["Call Change in OI"].sum()
        total_put_oi = df["Put Change in OI"].sum()

        st.subheader("📊 OI Summary Chart")
        summary_df = pd.DataFrame({
            "Side": ["Calls", "Puts"],
            "Change in OI": [total_call_oi, total_put_oi]
        })

        bar_chart = alt.Chart(summary_df).mark_bar().encode(
            x="Side",
            y="Change in OI",
            color=alt.condition(
                alt.datum.Side == "Calls", 
                alt.value("green"), 
                alt.value("red")
            ),
            tooltip=["Side", "Change in OI"]
        ).properties(
            width=400,
            height=300,
            title="Total Change in Open Interest"
        )
        st.altair_chart(bar_chart, use_container_width=True)

    except Exception as e:
        st.error(f"Error fetching data: {e}")

# --- Tab 2: LTP & OI Trends ---
with tab2:
    st.subheader("📈 Historical Trends: LTP and Change in OI")

    if os.path.exists(DATA_FILE):
        try:
            hist_data = pd.read_csv(DATA_FILE)
            hist_data['timestamp'] = pd.to_datetime(hist_data['timestamp'])
            
            # User selects strike price
            strike_options = sorted(hist_data['strikePrice'].unique())
            selected_strike = st.selectbox("Select Strike Price", strike_options)

            filtered_data = hist_data[hist_data['strikePrice'] == selected_strike]

            if not filtered_data.empty:
                c1, c2 = st.columns(2)

                # LTP trend
                with c1:
                    st.markdown(f"### 📉 LTP Trend for {selected_strike}")
                    ltp_chart = alt.Chart(filtered_data).mark_line().encode(
                        x="timestamp:T",
                        y=alt.Y("value:Q", title="Last Traded Price"),
                        color="type:N"
                    ).properties(width=500, height=250)
                    st.altair_chart(ltp_chart, use_container_width=True)

                # OI trend
                with c2:
                    st.markdown(f"### 📉 Change in OI Trend for {selected_strike}")
                    oi_chart = alt.Chart(filtered_data).mark_line().encode(
                        x="timestamp:T",
                        y=alt.Y("changeoi:Q", title="Change in Open Interest"),
                        color="type:N"
                    ).properties(width=500, height=250)
                    st.altair_chart(oi_chart, use_container_width=True)

            else:
                st.warning("No historical data available for this strike price.")

        except Exception as e:
            st.error(f"Error loading historical data: {e}")
    else:
        st.info("No historical data file found. Please run the data collector script.")

# Auto-refresh page if enabled
if enable_auto_refresh:
    st.experimental_rerun()
