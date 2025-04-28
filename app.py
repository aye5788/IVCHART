# app.py
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# Load ORATS token from secrets
ORATS_API_TOKEN = st.secrets["orats"]["token"]

st.title("📈 Option IV Tracker (Historical, Powered by ORATS)")

# User Inputs
ticker = st.text_input("Enter Ticker (e.g., SPY)", "CSCO")
strike_price = st.number_input("Strike Price", value=55.0, format="%.2f")
expiration_date = st.date_input("Expiration Date", datetime(2025, 5, 16))
start_date = st.date_input("Start pulling data from", datetime(2024, 1, 1))
option_type = st.selectbox("Option Type", ["Call", "Put"])

if st.button("Fetch and Plot IV History"):

    url = "https://api.orats.io/datav2/hist/strikes"

    params = {
        "token": ORATS_API_TOKEN,
        "ticker": ticker.upper(),
        "startDate": start_date.strftime("%Y-%m-%d"),
        "fields": "tradeDate,expirDate,strike,callMidIv,putMidIv"
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        raw = response.json()
        data = raw.get("data", [])

        if not data:
            st.warning("No historical data returned.")
        else:
            # Convert to DataFrame
            df = pd.DataFrame(data)

            # Filter for matching strike and expiration
            df = df[
                (df["strike"] == float(strike_price)) &
                (df["expirDate"] == expiration_date.strftime("%Y-%m-%d"))
            ]

            if df.empty:
                st.warning("No matching strike/expiration found in history.")
            else:
                df['tradeDate'] = pd.to_datetime(df['tradeDate'])
                df = df.sort_values('tradeDate')

                if option_type.lower() == "call":
                    y_col = "callMidIv"
                else:
                    y_col = "putMidIv"

                fig = px.line(df, x="tradeDate", y=y_col, 
                              title=f"{ticker.upper()} {option_type.upper()} {strike_price} IV Over Time",
                              labels={y_col: "Implied Volatility (IV)", "tradeDate": "Trade Date"})

                st.plotly_chart(fig)
    else:
        st.error(f"Failed to fetch data. Status code: {response.status_code}")

