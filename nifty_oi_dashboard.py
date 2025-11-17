import streamlit as st
import pandas as pd
import requests
import numpy as np
import altair as alt
from datetime import datetime

st.set_page_config(layout="wide", page_title="Nifty Option Chain Dashboard")

# Helper function to format large numbers
def format_num(num):
    return f"{num/1e5:.2f}L" if abs(num) > 1e5 else f"{num/1e3:.2f}K"

# Load historical trend data
@st.cache_data
def load_trend_data():
    try:
        return pd.read_csv("historical_data.csv", parse_dates=["time"])
    except FileNotFoundError:
        st.warning("Historical data file not found. Please upload historical_data.csv.")
        return pd.DataFrame()

# Fetch Option Chain data
@st.cache_data(ttl=90)
def fetch_option_chain():
    try:
        url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()['records']['data']
    except Exception:
        st.error("Unable to fetch option chain data from NSE.")
        return pd.DataFrame(), None

    formatted_rows = []
    underlying_value = None
    timestamp = None

    for entry in data:
        strike_price = entry.get("strikePrice")
        if "CE" in entry:
            ce_data = entry["CE"]
            underlying_value = ce_data.get("underlyingValue", underlying_value)
            timestamp = ce_data.get("timestamp", timestamp)
        else:
            ce_data = {}

        if "PE" in entry:
            pe_data = entry["PE"]
        else:
            pe_data = {}

        formatted_rows.append({
            "Strike Price": strike_price,
            "Call OI": ce_data.get("openInterest", 0),
            "Call Chg OI": ce_data.get("changeinOpenInterest", 0),
            "Call LTP": ce_data.get("lastPrice", 0),
            "Put OI": pe_data.get("openInterest", 0),
            "Put Chg OI": pe_data.get("changeinOpenInterest", 0),
            "Put LTP": pe_data.get("lastPrice", 0),
        })

    df = pd.DataFrame(formatted_rows)
    return df, underlying_value, timestamp

# Main app tabs
tabs = st.tabs(["Option Chain Dashboard", "LTP Trend"])

# 🟢 TAB 1: Option Chain Dashboard
with tabs[0]:
    df, spot_price, timestamp = fetch_option_chain()

    if df.empty:
        st.stop()

    st.title("🔥 NIFTY Option Chain Dashboard")

    # Format data
    df_styled = df.copy()
    df_styled["Call OI"] = df_styled["Call OI"].apply(format_num)
    df_styled["Put OI"] = df_styled["Put OI"].apply(format_num)

    # Highlight nearest strike price to spot
    nearest_strike = df.iloc[(df["Strike Price"] - spot_price).abs().argmin()]["Strike Price"]

    # Show OI table
    st.markdown(f"### Option Chain (Nearest Strike: `{nearest_strike}`, Spot: `{spot_price}`)")
    
    st.dataframe(
        df.style.apply(
            lambda x: ["background-color: yellow" if v == nearest_strike else "" for v in x["Strike Price"]],
            axis=1,
        ),
        height=600
    )

    # OI Summary
    total_call_oi = df["Call OI"].replace("-", 0).astype(float).sum()
    total_put_oi = df["Put OI"].replace("-", 0).astype(float).sum()
    st.subheader("📊 Open Interest Summary")
    st.write(f"**Total Call OI**: {format_num(total_call_oi)}")
    st.write(f"**Total Put OI**: {format_num(total_put_oi)}")

# 🔴 TAB 2: LTP Trend
with tabs[1]:
    st.title("📈 Last Traded Price Trend")
    trend_data = load_trend_data()

    if trend_data.empty:
        st.stop()

    strike_options = sorted(trend_data['strike_price'].unique())
    selected_strike = st.selectbox("Select Strike Price for Trend", strike_options)

    trend_df = trend_data[trend_data['strike_price'] == selected_strike].copy()
    trend_df["total_ltp"] = trend_df["call_ltp"] + trend_df["put_ltp"]
    trend_df_melted = trend_df.melt(
        id_vars=["time"],
        value_vars=["call_ltp", "put_ltp", "total_ltp"],
        var_name="Type",
        value_name="LTP"
    )

    # Altair Line Chart
    chart = alt.Chart(trend_df_melted).mark_line(point=True).encode(
        x="time:T",
        y="LTP:Q",
        color=alt.Color("Type:N", scale=alt.Scale(
            domain=["call_ltp", "put_ltp", "total_ltp"],
            range=["green", "red", "blue"]
        )),
        tooltip=["time:T", "Type:N", "LTP:Q"]
    ).properties(
        width=800,
        height=400,
        title=f"LTP Trend for Strike {selected_strike}"
    )

    st.altair_chart(chart, use_container_width=True)
    st.info("This graph shows how Call, Put, and combined LTP have changed over time.")

