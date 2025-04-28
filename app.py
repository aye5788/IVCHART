# app.py
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# Load ORATS API token from Streamlit secrets
ORATS_API_TOKEN = st.secrets["orats"]["token"]

st.title("📈 Option IV Tracker (Powered by ORATS)")

# Inputs
ticker = st.text_input("Enter Ticker (e.g., SPY)", "SPY")
start_date = st.date_input("Start Date", datetime(2024, 1, 1))
option_type = st.selectbox("Option Type", ["call", "put"])
strike_price = st.text_input("Strike Price (Optional)", "")

if st.button("Fetch IV Data"):

    # Form ORATS API URL
    url = "https://api.orats.io/datav2/option-history"

    params = {
        "token": ORATS_API_TOKEN,
        "ticker": ticker.upper(),
        "startDate": start_date.strftime("%Y-%m-%d"),
        "optionType": option_type,
    }

    if strike_price:
        params["strikePrice"] = strike_price

    # API Call
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()

        if not data:
            st.warning("No data returned. Please check your inputs.")
        else:
            # Parse data
            iv_data = []
            for record in data:
                if "tradeDate" in record and "ivMid" in record:
                    iv_data.append({
                        "Date": record["tradeDate"],
                        "IV": record["ivMid"]
                    })

            df = pd.DataFrame(iv_data)
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values("Date")

            # Plot
            fig = px.line(df, x="Date", y="IV", title=f"{ticker.upper()} {option_type.upper()} IV Over Time")
            st.plotly_chart(fig)
    else:
        st.error(f"Error fetching data: {response.status_code}")
