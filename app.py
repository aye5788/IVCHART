# app.py
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# Load ORATS token from secrets
ORATS_API_TOKEN = st.secrets["orats"]["token"]

st.title("📈 Multi-Option IV Tracker (Powered by ORATS)")

# Initialize session state for dynamic options
if "num_options" not in st.session_state:
    st.session_state.num_options = 1

# Global Inputs
ticker = st.text_input("Enter Ticker (e.g., SPY)", "CSCO")
start_date = st.date_input("Start pulling data from", datetime(2024, 1, 1))

st.subheader("📋 Options to Track")

# Add/Remove Option Buttons
cols = st.columns([1, 1])
with cols[0]:
    if st.button("+ Add Option"):
        st.session_state.num_options += 1
with cols[1]:
    if st.button("- Remove Option") and st.session_state.num_options > 1:
        st.session_state.num_options -= 1

# Collect all option inputs
option_inputs = []
for i in range(st.session_state.num_options):
    st.markdown(f"**Option {i + 1}**")
    strike = st.number_input(f"Strike Price #{i + 1}", value=55.0, format="%.2f", key=f"strike_{i}")
    expiration = st.date_input(f"Expiration Date #{i + 1}", datetime(2025, 5, 16), key=f"expiration_{i}")
    option_type = st.selectbox(f"Option Type #{i + 1}", ["Call", "Put"], key=f"type_{i}")
    option_inputs.append({
        "strike": strike,
        "expiration": expiration,
        "type": option_type
    })

# Fetch Data Button
if st.button("Fetch and Plot IV History"):

    # Generate only BUSINESS DAYS
    dates = pd.date_range(start=start_date, end=datetime.today(), freq='B')

    all_data = []

    with st.spinner(f"Fetching IV data for {len(option_inputs)} option(s)..."):

        for idx, option in enumerate(option_inputs):
            option_label = f"{option['strike']} {option['type'][0]} {option['expiration'].strftime('%m/%d/%y')}"
            option_iv_series = []

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
                            record.get("strike") == float(option['strike']) and
                            record.get("expirDate") == option['expiration'].strftime("%Y-%m-%d")
                        ):
                            trade_date = pd.to_datetime(record.get("tradeDate"))
                            if option["type"].lower() == "call":
                                iv = record.get("callMidIv")
                            else:
                                iv = record.get("putMidIv")
                            if iv is not None:
                                option_iv_series.append({"tradeDate": trade_date, option_label: iv * 100})
                elif response.status_code != 404:
                    st.warning(f"Failed to fetch data for {date.strftime('%Y-%m-%d')} (status {response.status_code})")

            if option_iv_series:
                df_option = pd.DataFrame(option_iv_series)
                df_option = df_option.set_index("tradeDate")
                all_data.append(df_option)
            else:
                st.warning(f"No data found for {option_label}.")

    if not all_data:
        st.error("No data found for any options.")
    else:
        # Merge all options on tradeDate
        df_final = pd.concat(all_data, axis=1).reset_index()
        df_final = df_final.sort_values("tradeDate")

        # Define custom color palette
        custom_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", 
                         "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]

        # Plot
        fig = px.line(
            df_final,
            x="tradeDate",
            y=df_final.columns[1:], 
            color_discrete_sequence=custom_colors,
            title=f"{ticker.upper()} - Implied Volatility (%) Over Time",
            labels={"value": "Implied Volatility (%)", "tradeDate": "Trade Date", "variable": "Option"}
        )

        st.plotly_chart(fig)

        # Display IV Changes per Option
        st.subheader("📈 IV Changes Over Selected Period")

        for col in df_final.columns[1:]:  # skip tradeDate
            start_iv = df_final[col].dropna().iloc[0]
            end_iv = df_final[col].dropna().iloc[-1]
            iv_change = end_iv - start_iv
            iv_pct_change = (iv_change / start_iv) * 100

            st.metric(
                label=f"{col} IV Change",
                value=f"{iv_change:.2f}%",
                delta=f"{iv_pct_change:.2f}%"
            )
            # Phase 1: Calendar Spread Metrics (only if exactly 2 legs selected)
if len(df_final.columns[1:]) == 2:
    opt1, opt2 = df_final.columns[1:]

    # Extract IV series
    iv1 = df_final[opt1].dropna()
    iv2 = df_final[opt2].dropna()

    if len(iv1) > 0 and len(iv2) > 0:
        iv1_first, iv1_last = iv1.iloc[0], iv1.iloc[-1]
        iv2_first, iv2_last = iv2.iloc[0], iv2.iloc[-1]

        # Get expiration dates from option_inputs
        exp1 = [o['expiration'] for o in option_inputs if f"{o['strike']} {o['type'][0]} {o['expiration'].strftime('%m/%d/%y')}" == opt1][0]
        exp2 = [o['expiration'] for o in option_inputs if f"{o['strike']} {o['type'][0]} {o['expiration'].strftime('%m/%d/%y')}" == opt2][0]

        # Assign short and long legs based on expiration
        if exp1 < exp2:
            short_iv_now, long_iv_now = iv1_last, iv2_last
            short_iv_open, long_iv_open = iv1_first, iv2_first
            short_exp, long_exp = exp1, exp2
        else:
            short_iv_now, long_iv_now = iv2_last, iv1_last
            short_iv_open, long_iv_open = iv2_first, iv1_first
            short_exp, long_exp = exp2, exp1

        # Calculate DTEs based on first trade date
        dte_short = (short_exp - df_final['tradeDate'].min()).days
        dte_long = (long_exp - df_final['tradeDate'].min()).days

        # Metrics
        iv_crush = short_iv_now - short_iv_open
        iv_ratio = short_iv_now / long_iv_now if long_iv_now else float("nan")
        iv_spread = short_iv_now - long_iv_now
        slope = (long_iv_now - short_iv_now) / (dte_long - dte_short) if (dte_long - dte_short) != 0 else float("nan")

        # Display
        st.subheader("📊 Calendar Spread Metrics")

        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="IV Crush (Short Leg)", value=f"{iv_crush:.2f}%", delta=f"{(iv_crush / short_iv_open * 100):.2f}%")
            st.metric(label="IV Spread", value=f"{iv_spread:.2f}%")
        with col2:
            st.metric(label="IV Ratio (Short / Long)", value=f"{iv_ratio:.2f}")
            st.metric(label="IV Curve Slope", value=f"{slope:.4f} per DTE")


