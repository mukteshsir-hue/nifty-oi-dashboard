import streamlit as st
import pandas as pd
import altair as alt

DATA_FILE = "data/oi_trend.csv"

st.set_page_config(page_title="Nifty OI Trend Dashboard", layout="wide")
st.title("📈 Nifty Options Trend Dashboard")

try:
    df = pd.read_csv(DATA_FILE)
except FileNotFoundError:
    st.error("No data found. Please start the data collector.")
    st.stop()

df['timestamp'] = pd.to_datetime(df['timestamp'])

tab1, tab2, tab3 = st.tabs(["Call & Put LTP", "Call & Put OI", "Total OI"])

with tab1:
    st.header("Call vs Put LTP Trend")
    line_chart = alt.Chart(df).mark_line(point=True).encode(
        x='timestamp:T',
        y=alt.Y('call_ltp:Q', axis=alt.Axis(title='Price')),
        color=alt.value("green")
    ).properties(title="Call LTP")

    line_chart2 = alt.Chart(df).mark_line(point=True).encode(
        x='timestamp:T',
        y=alt.Y('put_ltp:Q'),
        color=alt.value("red")
    ).properties(title="Put LTP")

    st.altair_chart((line_chart + line_chart2).interactive(), use_container_width=True)

with tab2:
    st.header("Call vs Put OI Trend")
    call_oi_chart = alt.Chart(df).mark_line(point=True).encode(
        x='timestamp:T',
        y='call_oi:Q',
        color=alt.value("green")
    ).properties(title="Call OI")

    put_oi_chart = alt.Chart(df).mark_line(point=True).encode(
        x='timestamp:T',
        y='put_oi:Q',
        color=alt.value("red")
    ).properties(title="Put OI")

    st.altair_chart((call_oi_chart + put_oi_chart).interactive(), use_container_width=True)

with tab3:
    st.header("Total OI Trend (Call + Put)")
    total_oi_chart = alt.Chart(df).mark_line(point=True).encode(
        x='timestamp:T',
        y='total_oi:Q',
        color=alt.value("blue")
    ).properties(title="Total OI")

    st.altair_chart(total_oi_chart.interactive(), use_container_width=True)
