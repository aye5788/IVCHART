# app.py
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# Load ORATS token from Streamlit secrets
ORATS_API_TOKEN = st.secrets["orats"]["token"]

st.title("📈 Option IV Tracker (Historical, Powered by ORATS)")

# User Inputs
ticker = st.text_input("Enter Ticker (e.g., SPY)", "CSCO")
strike_price = st.number_input("Strike Price", value=55.0, format="%.2f")
expiration_date = st.date_input("Expiration Date", datetime(2025, 5, 16))
start_date = st.date_input("Start pulling data from", datetime(2024, 1, 1))
option_type = st.selectbox("Option Type", ["Call", "Put"])

if st.button("Fetch and Plot IV History"):

    # Generate only BUSINESS DAYS
    dates = pd.date_range(start=start_date, end=datetime.today(), freq='B')
    all_data = []

    with st.spinner(f"Fetching IV data from {start_date.strftime('%Y-%m-%d')} to today..."):

        for date in dates:
            params = {
                "token": ORATS_API_TOKEN,
                "ticker": ticker.upper(),
                "tradeDate": date.strftime("%Y-%m-%d"),
                "fields": "tradeDate,expirDate,strike,callMidIv,putMidIv"
            }
            response = requests.get("https://api.orats.io/datav2/hist/strikes", params=params)

            if response.status_code == 200:
                day_data = response.json().get("data", [])
                for record in day_data:
                    if (
                        record.get("strike") == float(strike_price) and
                        record.get("expirDate") == expiration_date.strftime("%Y-%m-%d")
                    ):
                        all_data.append(record)
            elif response.status_code != 404:
                st.warning(f"Failed to fetch data for {date.strftime('%Y-%m-%d')} (status {response.status_code})")

    if not all_data:
        st.error("No matching strike and expiration found over the selected period.")
    else:
        df = pd.DataFrame(all_data)
        df['tradeDate'] = pd.to_datetime(df['tradeDate'])
        df = df.sort_values('tradeDate')

        if option_type.lower() == "call":
            y_col = "callMidIv"
        else:
            y_col = "putMidIv"

        # Convert IV from decimal to percentage
        df[y_col] = df[y_col] * 100

        # Plot
        fig = px.line(df, x="tradeDate", y=y_col,
                      title=f"{ticker.upper()} {option_type.upper()} {strike_price} IV Over Time",
                      labels={y_col: "Implied Volatility (%)", "tradeDate": "Trade Date"})

        st.plotly_chart(fig)

        # Calculate and display IV change
        start_iv = df[y_col].iloc[0]
        end_iv = df[y_col].iloc[-1]
        iv_change = end_iv - start_iv
        iv_pct_change = (iv_change / start_iv) * 100

        st.subheader("📈 IV Change Over Selected Period")
        st.metric(label="IV Change", value=f"{iv_change:.2f}%", delta=f"{iv_pct_change:.2f}%")


