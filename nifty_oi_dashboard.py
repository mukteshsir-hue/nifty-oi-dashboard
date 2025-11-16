import streamlit as st
import requests
import pandas as pd
import time
import altair as alt

# NSE Option Chain URL
NSE_OPTION_CHAIN_URL = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"

# Headers to avoid NSE blocking
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://www.nseindia.com/option-chain"
}

# Fetch option chain data
def fetch_option_chain():
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=HEADERS)
        response = session.get(NSE_OPTION_CHAIN_URL, headers=HEADERS)
        data = response.json()
        return data.get("records", {}).get("data", [])
    except Exception:
        return []

# Extract only 10 strikes above and below spot
def extract_strike_data(records, spot_price, num_strikes=10):
    strikes = []
    for entry in records:
        if "CE" in entry and "PE" in entry:
            strike = entry["strikePrice"]
            if strike <= spot_price + num_strikes * 50 and strike >= spot_price - num_strikes * 50:
                strikes.append({
                    "strikePrice": strike,
                    "CE.changeinOpenInterest": entry["CE"]["changeinOpenInterest"],
                    "PE.changeinOpenInterest": entry["PE"]["changeinOpenInterest"]
                })

    df = pd.DataFrame(strikes).sort_values(by="strikePrice")
    # Select 20 strikes closest to spot
    if not df.empty:
        df = df.iloc[(df['strikePrice'] - spot_price).abs().argsort()][:20]
    return df.sort_values(by="strikePrice")

# Streamlit Dashboard
def run_dashboard():
    st.set_page_config(page_title="Nifty OI Change Tracker", layout="wide")
    st.title("📊 Live Nifty OI Change Tracker")

    # Sidebar Controls
    refresh_interval = st.sidebar.selectbox("⏱️ Auto Refresh Interval", ["1 min", "30 sec"])
    auto_refresh = st.sidebar.checkbox("Enable Auto Refresh", value=True)

    refresh_time = 60 if refresh_interval == "1 min" else 30

    btn = st.button("🔄 Refresh Now")
    if btn:
        st.session_state.updated = time.time()

    # Main refresh loop
    while auto_refresh or st.session_state.get("updated"):
        with st.spinner("Fetching latest data..."):
            records = fetch_option_chain()

        if not records:
            st.error("Failed to fetch data. Try refreshing or check your connection.")
            break

        spot_price = next((d.get("CE", {}).get("underlyingValue") for d in records if "CE" in d), None)
        st.write(f"**Nifty Spot Price:** `{spot_price}`")

        df = extract_strike_data(records, spot_price)
        if df.empty:
            st.warning("Could not find strike data near spot price.")
            break

        # Display Strike-wise Change in OI Table
        st.subheader("Strike-wise Change in Open Interest (📉 PE | 📈 CE)")
        st.dataframe(df)

        # Calculate Summaries
        total_ce_oi = df["CE.changeinOpenInterest"].sum()
        total_pe_oi = df["PE.changeinOpenInterest"].sum()
        diff = total_ce_oi - total_pe_oi

        st.write(f"📈 **Total Change in OI (Calls):** {total_ce_oi:,}")
        st.write(f"📉 **Total Change in OI (Puts):** {total_pe_oi:,}")
        st.write(f"⚖️ **Net Weight (Calls - Puts):** {diff:,}")

        # Visualization with Altair
        st.subheader("OI Change Visualization")
        chart_data = df.melt(id_vars=["strikePrice"], var_name="Type", value_name="Change in OI")
        chart = alt.Chart(chart_data).mark_bar().encode(
            x="strikePrice:O",
            y="Change in OI:Q",
            color="Type:N",
            tooltip=["strikePrice", "Type", "Change in OI"]
        )
        st.altair_chart(chart, use_container_width=True)

        # Signal based on weight
        st.subheader("📡 Trade Signal")
        threshold = st.number_input("Set Weight Threshold for Signal", min_value=0, value=50000, step=5000)

        if diff > threshold:
            st.success(f"📈 **Bullish Signal** (Calls dominant by `{diff:,}`)")
        elif diff < -threshold:
            st.error(f"📉 **Bearish Signal** (Puts dominant by `{abs(diff):,}`)")
        else:
            st.info(f"⚪ No clear signal (Weight `{diff:,}` within threshold)")

        if auto_refresh:
            time.sleep(refresh_time)
        else:
            break

if __name__ == "__main__":
    run_dashboard()
