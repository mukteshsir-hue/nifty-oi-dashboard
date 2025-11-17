import streamlit as st
import pandas as pd
import altair as alt
import os

st.set_page_config(page_title="Nifty OI Dashboard", layout="wide")
st.title("📊 Nifty Open Interest Dashboard")

DATA_PATH = "nifty_oi_data.csv"

if os.path.exists(DATA_PATH):
    df = pd.read_csv(DATA_PATH, parse_dates=["timestamp"])
else:
    st.warning("Data not found. Please run `data_collector.py` to start collecting data.")
    st.stop()

tab1, tab2 = st.tabs(["OI Summary", "Trends by Strike"])

with tab1:
    st.subheader("📈 Open Interest Summary (Latest Snapshot)")
    latest_time = df["timestamp"].max()
    latest_df = df[df["timestamp"] == latest_time]

    pivot_df = latest_df.pivot(index="strikePrice", columns="side", values=["changeInOI", "lastPrice"])
    pivot_df.columns = [f"{val} {side}" for val, side in pivot_df.columns]
    pivot_df.reset_index(inplace=True)

    pivot_df["Total LTP"] = pivot_df["lastPrice CE"] + pivot_df["lastPrice PE"]
    pivot_df["Weight Diff (OI)"] = pivot_df["changeInOI CE"] - pivot_df["changeInOI PE"]

    underlying_value = latest_df["underlyingValue"].iloc[0]
    nearest_strike = min(pivot_df["strikePrice"], key=lambda x: abs(x - underlying_value))

    def highlight_row(row):
        return ['background-color: yellow' if row['strikePrice'] == nearest_strike else '' for _ in row]

    st.dataframe(pivot_df.style.apply(highlight_row, axis=1), use_container_width=True, height=600)

    total_call_oi = latest_df[latest_df["side"] == "CE"]["changeInOI"].sum()
    total_put_oi = latest_df[latest_df["side"] == "PE"]["changeInOI"].sum()

    st.markdown(
        f"""
        <h4>📌 Open Interest Summary:</h4>
        <ul>
            <li><strong>Total Call OI Change:</strong> <span style="color:green;">{total_call_oi:,}</span></li>
            <li><strong>Total Put OI Change:</strong> <span style="color:red;">{total_put_oi:,}</span></li>
        </ul>
        """, unsafe_allow_html=True
    )

with tab2:
    st.subheader("📈 Trends by Strike Price")
    strikes = sorted(df["strikePrice"].unique())
    strike = st.selectbox("Select Strike Price", strikes)

    strike_data = df[df["strikePrice"] == strike]

    st.write("### Open Interest Change Trend")
    oi_chart = alt.Chart(strike_data).mark_line().encode(x="timestamp:T", y="changeInOI:Q", color="side:N")
    st.altair_chart(oi_chart, use_container_width=True)

    st.write("### Last Traded Price (LTP) Trend")
    ltp_chart = alt.Chart(strike_data).mark_line().encode(x="timestamp:T", y="lastPrice:Q", color="side:N")
    st.altair_chart(ltp_chart, use_container_width=True)

    st.write("### Total LTP Trend (Call + Put)")
    strike_data["Total_LTP"] = strike_data[strike_data["side"] == "CE"]["lastPrice"].reset_index(drop=True) + strike_data[strike_data["side"] == "PE"]["lastPrice"].reset_index(drop=True)
    total_ltp_chart = alt.Chart(strike_data).mark_line(color="black").encode(x="timestamp:T", y="Total_LTP:Q")
    st.altair_chart(total_ltp_chart, use_container_width=True)
