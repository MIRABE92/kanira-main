import time
from datetime import date, timedelta
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
from scipy.stats import norm

st.set_page_config(page_title="Kanira Advisor | 2M Futures, Greeks & Time Value Dashboard", layout="wide")
st.title("📈 2-Month Futures, Option Greeks, Time Value & 52-Week Custom-Days Dashboard")

def get_two_month_expiries(expiry_weekday=3):
    today = date.today()
    expiries = []
    labels = ["Near Month (1st Month)", "Next Month (2nd Month)"]
    m = 0
    while len(expiries) < 2:
        yr = today.year + (today.month + m - 1) // 12
        mo = (today.month + m - 1) % 12 + 1
        nxt_mo = date(yr + 1, 1, 1) if mo == 12 else date(yr, mo + 1, 1)
        last_day = nxt_mo - timedelta(days=1)
        offset = (last_day.weekday() - expiry_weekday) % 7
        m_dt = last_day - timedelta(days=offset)
        if m_dt > today:
            expiries.append((f"{labels[len(expiries)]} — {m_dt.strftime('%d %b %Y')}", (m_dt - today).days))
        m += 1
    return expiries

def calc_derivatives(S, K, T, r, q, sigma):
    fut_px = S * np.exp((r - q) * T)
    basis = fut_px - S
    c_intr = max(0.0, S - K)
    p_intr = max(0.0, K - S)
    if T <= 0:
        return {
            "fut": fut_px, "basis": basis,
            "c_px": c_intr, "p_px": p_intr,
            "c_intr": c_intr, "p_intr": p_intr,
            "c_tv": 0.0, "p_tv": 0.0,
            "c_delta": 1.0 if S > K else 0.0, "p_delta": -1.0 if S < K else 0.0,
            "gamma": 0.0, "c_theta": 0.0, "p_theta": 0.0, "vega": 0.0, "c_rho": 0.0, "p_rho": 0.0
        }

    sqrt_T = np.sqrt(T)
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    pdf_d1 = norm.pdf(d1)

    c_px = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    p_px = K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)
    gamma = (np.exp(-q * T) * pdf_d1) / (S * sigma * sqrt_T)
    vega = (S * np.exp(-q * T) * pdf_d1 * sqrt_T) / 100.0
    c_delta = np.exp(-q * T) * norm.cdf(d1)
    p_delta = np.exp(-q * T) * (norm.cdf(d1) - 1.0)
    c_theta = (-(S * np.exp(-q * T) * pdf_d1 * sigma) / (2 * sqrt_T) - r * K * np.exp(-r * T) * norm.cdf(d2) + q * S * np.exp(-q * T) * norm.cdf(d1)) / 365.0
    p_theta = (-(S * np.exp(-q * T) * pdf_d1 * sigma) / (2 * sqrt_T) + r * K * np.exp(-r * T) * norm.cdf(-d2) - q * S * np.exp(-q * T) * norm.cdf(-d1)) / 365.0
    c_rho = (K * T * np.exp(-r * T) * norm.cdf(d2)) / 100.0
    p_rho = (-K * T * np.exp(-r * T) * norm.cdf(-d2)) / 100.0

    return {
        "fut": fut_px, "basis": basis,
        "c_px": c_px, "p_px": p_px,
        "c_intr": c_intr, "p_intr": p_intr,
        "c_tv": max(0.0, c_px - c_intr), "p_tv": max(0.0, p_px - p_intr),
        "c_delta": c_delta, "p_delta": p_delta,
        "gamma": gamma, "c_theta": c_theta, "p_theta": p_theta,
        "vega": vega, "c_rho": c_rho, "p_rho": p_rho
    }

with st.sidebar:
    st.header("⚙️ 2-Month Contract Settings")
    ticker = st.text_input("NSE Symbol (add .NS)", value="^NSEI")
    use_live = st.checkbox("Fetch Live Market Data (Yahoo Finance)", value=False)
    auto_refresh = st.checkbox("Auto-Refresh Live Every 5s", value=False)
    exp_day = st.selectbox("Monthly Expiry Day", [("Thursday (Nifty / Stock F&O)", 3), ("Wednesday (Bank Nifty)", 2), ("Tuesday (FinNifty)", 1)], format_func=lambda x: x[0])
    strike = st.number_input("Strike Price (K)", value=24000.0, step=50.0)
    iv = st.slider("Implied Volatility (IV %)", 5.0, 100.0, 14.5, 0.5) / 100.0
    r = st.number_input("Risk-Free Rate (%)", value=6.75, step=0.25) / 100.0
    q = st.number_input("Dividend Yield (%)", value=1.20, step=0.10) / 100.0

if use_live:
    try:
        hist = yf.Ticker(ticker).history(period="1y")
        spot = float(hist["Close"].iloc[-1])
        high_52 = float(hist["High"].max())
        low_52 = float(hist["Low"].min())
    except Exception as e:
        st.warning(f"Live feed unavailable ({e}). Using manual values.")
        spot, high_52, low_52 = 24150.0, 26277.0, 21281.0
else:
    spot = st.sidebar.number_input("Spot Price (S)", value=24150.0, step=10.0)
    high_52 = st.sidebar.number_input("52-Week High", value=26277.0, step=10.0)
    low_52 = st.sidebar.number_input("52-Week Low", value=21281.0, step=10.0)

expiries = get_two_month_expiries(exp_day[1])
rows = []
for label, dte in expiries:
    res = calc_derivatives(spot, strike, dte / 365.0, r, q, iv)
    rows.append({
        "2-Month Contract": label, "DTE": dte,
        "Futures Fair Value (₹)": round(res["fut"], 2), "Basis / Carry (₹)": round(res["basis"], 2),
        "CALL Prem (₹)": round(res["c_px"], 2), "PUT Prem (₹)": round(res["p_px"], 2),
        "Call Intrinsic": round(res["c_intr"], 2), "Call Time Value": round(res["c_tv"], 2),
        "Put Intrinsic": round(res["p_intr"], 2), "Put Time Value": round(res["p_tv"], 2),
        "Call Δ": round(res["c_delta"], 3), "Put Δ": round(res["p_delta"], 3),
        "Gamma Γ": round(res["gamma"], 5), "Call Θ/day": round(res["c_theta"], 2),
        "Put Θ/day": round(res["p_theta"], 2), "Vega ν": round(res["vega"], 2),
        "Call ρ": round(res["c_rho"], 2), "Put ρ": round(res["p_rho"], 2)
    })

df = pd.DataFrame(rows)
cal_spread = df.loc[1, "Futures Fair Value (₹)"] - df.loc[0, "Futures Fair Value (₹)"]
range_pct = ((spot - low_52) / (high_52 - low_52) * 100) if high_52 > low_52 else 50.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Spot Price (S)", f"₹ {spot:,.2f}", f"52W Pos: {range_pct:.1f}%")
c2.metric("1st Month Futures", f"₹ {df.loc[0, 'Futures Fair Value (₹)']:,.2f}", f"Carry: +₹ {df.loc[0, 'Basis / Carry (₹)']:,.2f}")
c3.metric("2nd Month Futures", f"₹ {df.loc[1, 'Futures Fair Value (₹)']:,.2f}", f"Carry: +₹ {df.loc[1, 'Basis / Carry (₹)']:,.2f}")
c4.metric("2-Month Calendar Spread", f"₹ {cal_spread:,.2f}", f"52W Range: ₹{low_52:,.0f} – ₹{high_52:,.0f}")
st.progress(min(max(range_pct / 100.0, 0.0), 1.0))

st.divider()
st.subheader("⏳ Time Value Breakdown & Custom-Days 52-Week High/Low Pricing")

sc1, sc2 = st.columns([1, 2])
with sc1:
    selected_idx = st.selectbox("Select Contract for Scenario", [0, 1], format_func=lambda i: expiries[i][0])
    contract_dte = expiries[selected_idx][1]
    days_elapsed = st.slider("Custom Days Elapsed to Reach 52W High/Low", 0, contract_dte, min(5, contract_dte))
    rem_dte = max(0, contract_dte - days_elapsed)
    st.info(f"**Total Contract DTE:** {contract_dte} days  \n**Days Elapsed:** {days_elapsed} days  \n**Remaining DTE at Target:** {rem_dte} days")

with sc2:
    T_rem = rem_dte / 365.0
    at_spot = calc_derivatives(spot, strike, T_rem, r, q, iv)
    at_high = calc_derivatives(high_52, strike, T_rem, r, q, iv)
    at_low = calc_derivatives(low_52, strike, T_rem, r, q, iv)

    scen_df = pd.DataFrame([
        {
            "Scenario (After Custom Days)": f"Current Spot (₹ {spot:,.0f})",
            "Futures Price (₹)": round(at_spot["fut"], 2),
            "CALL Total (₹)": round(at_spot["c_px"], 2),
            "CALL Intrinsic": round(at_spot["c_intr"], 2),
            "CALL Time Value": round(at_spot["c_tv"], 2),
            "PUT Total (₹)": round(at_spot["p_px"], 2),
            "PUT Intrinsic": round(at_spot["p_intr"], 2),
            "PUT Time Value": round(at_spot["p_tv"], 2)
        },
        {
            "Scenario (After Custom Days)": f"52-Week High (₹ {high_52:,.0f})",
            "Futures Price (₹)": round(at_high["fut"], 2),
            "CALL Total (₹)": round(at_high["c_px"], 2),
            "CALL Intrinsic": round(at_high["c_intr"], 2),
            "CALL Time Value": round(at_high["c_tv"], 2),
            "PUT Total (₹)": round(at_high["p_px"], 2),
            "PUT Intrinsic": round(at_high["p_intr"], 2),
            "PUT Time Value": round(at_high["p_tv"], 2)
        },
        {
            "Scenario (After Custom Days)": f"52-Week Low (₹ {low_52:,.0f})",
            "Futures Price (₹)": round(at_low["fut"], 2),
            "CALL Total (₹)": round(at_low["c_px"], 2),
            "CALL Intrinsic": round(at_low["c_intr"], 2),
            "CALL Time Value": round(at_low["c_tv"], 2),
            "PUT Total (₹)": round(at_low["p_px"], 2),
            "PUT Intrinsic": round(at_low["p_intr"], 2),
            "PUT Time Value": round(at_low["p_tv"], 2)
        }
    ])
    st.dataframe(scen_df, use_container_width=True, hide_index=True)

st.divider()
st.subheader("📊 2-Month Option Premiums, Intrinsic/Time Value & Full Greeks")
st.dataframe(df, use_container_width=True, hide_index=True)

if auto_refresh:
    time.sleep(5)
    st.rerun()
