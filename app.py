import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# Load ORATS API token
ORATS_API_TOKEN = st.secrets["orats"]["token"]

st.title("📈 Option IV Tracker (Powered by ORATS)")

# Inputs
ticker = st.text_input("Enter Ticker (e.g., SPY)", "SPY")
start_date = st.date_input("Start Date", datetime.today())
option_type = st.selectbox("Option Type", ["call", "put"])
strike_price = st.text_input("Strike Price (Optional)", "")
expiration_date = None
if strike_price:
    expiration_date = st.date_input("Expiration Date (Required if Strike Specified)", datetime.today())

if st.button("Fetch IV Data"):
    
    url = "https://api.orats.io/datav2/cores"

    iv_key = "callMidIv" if option_type == "call" else "putMidIv"

    params = {
        "token": ORATS_API_TOKEN,
        "ticker": ticker.upper(),
        "startdate": start_date.strftime("%Y-%m-%d"),
        "fields": f"quoteDate,expiration,strike,{iv_key}"
    }

    if strike_price:
        params["strikePrice"] = strike_price
        params["expiration"] = expiration_date.strftime("%Y-%m-%d")

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()

        if not data:
            st.warning("No data returned. Check your inputs.")
        else:
            iv_data = []
            for record in data:
                if record.get(iv_key) is not None:
                    iv_data.append({
                        "Date": record["quoteDate"],
                        "IV": record[iv_key]
                    })

            df = pd.DataFrame(iv_data)
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values("Date")

            fig = px.line(df, x="Date", y="IV", title=f"{ticker.upper()} {option_type.upper()} IV Over Time")
            st.plotly_chart(fig)
    else:
        st.error(f"Error fetching data: {response.status_code}")

