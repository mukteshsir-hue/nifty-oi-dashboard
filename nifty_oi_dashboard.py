import streamlit as st
import requests
import pandas as pd
import time
import altair as alt

NSE_OPTION_CHAIN_URL = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://www.nseindia.com/option-chain"
}

def fetch_option_chain():
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=HEADERS)
        response = session.get(NSE_OPTION_CHAIN_URL, headers=HEADERS)
        data = response.json()
        return data.get("records", {}).get("data", [])
    except Exception:
        return []

def extract_strike_data(records, spot_price, num_strikes=10):
    strikes = []
    for entry in records:
        if "CE" in entry and "PE" in entry:
            strike = entry["strikePrice"]
            if abs(strike - spot_price) <= num_strikes * 50:
                strikes.append({
                    "strikePrice": strike,
                    "CE.changeinOpenInterest": entry["CE"]["changeinOpenInterest"],
                    "PE.changeinOpenInterest": entry["PE"]["changeinOpenInterest"]
                })
    return pd.DataFrame(strikes).sort_values(by="strikePrice")

def run_dashboard():
    st.set_page_config(page_title="Nifty OI Change Tracker", layout="wide")
    st.title("📊 Live Nifty OI Change Tracker")

    refresh_interval = st.sidebar.selectbox("Auto Refresh Interval", ["1 min", "30 sec"])
    auto_refresh = st.sidebar.checkbox("Enable Auto Refresh", value=True)

    refresh_time = 60 if refresh_interval == "1 min" else 30

    if st.button("🔄 Refresh Now"):
        st.session_state.updated = time.time()

    while auto_refresh or st.session_state.get("updated"):
        with st.spinner("Fetching latest data..."):
            records = fetch_option_chain()

        if not records:
            st.error("Failed to fetch data. Try refreshing or check internet connection.")
            break

        spot_price = next((d.get("CE", {}).get("underlyingValue") for d in records if "CE" in d), None)
        st.write(f"**Nifty Spot Price:** {spot_price}")

        df = extract_strike_data(records, spot_price, num_strikes=10)

        st.subheader("Strike-wise Change in Open Interest")
        st.dataframe(df)

        total_ce_oi = df["CE.changeinOpenInterest"].sum()
        total_pe_oi = df["PE.changeinOpenInterest"].sum()
        diff = total_ce_oi - total_pe_oi

        st.write(f"📈 **Sum of Change in OI (Calls):** {total_ce_oi:,}")
        st.write(f"📉 **Sum of Change in OI (Puts):** {total_pe_oi:,}")
        st.write(f⚖️ **Net Weight (CE - PE):** {diff:,}")

        chart_data = df.melt(id_vars=["strikePrice"], var_name="Type", value_name="Change in OI")
        chart = alt.Chart(chart_data).mark_bar().encode(
            x="strikePrice:O",
            y="Change in OI:Q",
            color="Type:N"
        )
        st.altair_chart(chart, use_container_width=True)

        threshold = st.number_input("Weight Threshold for Signal", min_value=0, value=50000, step=5000)

        if diff > threshold:
            st.success(f"📈 Bullish Signal (CE > PE by {diff})")
        elif diff < -threshold:
            st.error(f"📉 Bearish Signal (PE > CE by {abs(diff)})")
        else:
            st.info("⚪ Neutral / No Trade")

        if auto_refresh:
            time.sleep(refresh_time)
        else:
            break

if __name__ == "__main__":
    run_dashboard()
