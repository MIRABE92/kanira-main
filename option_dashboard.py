import os, urllib.parse
from datetime import datetime
import pandas as pd
import streamlit as st

BRAND_NAME = "Kanira Advisor"
PARTNER_TAG = "Authorized Business Partner — Mirae Asset Sharekhan | Mumbai & Mira-Bhayandar"
WHATSAPP_NO = "919820000000"  # Replace with your 12-digit WhatsApp number

USERS = {
    "admin": {"pass": "kanira2026", "role": "Advisor Admin", "name": "Kanira Advisory Desk"},
    "client": {"pass": "hni2026", "role": "HNI Client", "name": "Privileged HNI Client"}
}

try:
    st.set_page_config(page_title=f"{BRAND_NAME} | 2-Month Futures & Option Greeks Terminal", layout="wide")
except Exception:
    pass

if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

if not st.session_state.auth_user:
    st.title(f"🏛️ {BRAND_NAME} — 2-Month Futures & Derivatives Terminal")
    st.caption(PARTNER_TAG)
    st.divider()

    col_login, col_lead = st.columns([1, 1.2], gap="large")
    with col_login:
        with st.form("opt_login_form"):
            st.subheader("🔐 Client & Advisor Sign In")
            u = st.text_input("Username", placeholder="admin or client").strip().lower()
            p = st.text_input("Password", type="password", placeholder="Enter access key")
            if st.form_submit_button("Unlock 2-Month Terminal", use_container_width=True, type="primary"):
                if u in USERS and USERS[u]["pass"] == p:
                    st.session_state.auth_user = USERS[u]
                    st.rerun()
                else:
                    st.error("Invalid credentials. Contact Kanira Advisor for access.")

    with col_lead:
        with st.form("opt_lead_form"):
            st.subheader("📞 Request Portal Access, Portfolio Review or Demat")
            l_name = st.text_input("Full Name")
            l_phone = st.text_input("Mobile / WhatsApp Number (+91)")
            l_service = st.selectbox("Primary Interest", [
                "Open Free Sharekhan Demat & F&O Account",
                "Book Free HNI Portfolio Health Review",
                "Request 2-Month Derivatives Terminal Access",
                "Covered Call & Portfolio Hedging Consultation"
            ])
            l_cap = st.selectbox("Investable / Trading Capital", ["₹5 Lakh – ₹25 Lakh", "₹25 Lakh – ₹1 Crore", "₹1 Crore+", "Starting New SIP / Trading"])
            if st.form_submit_button("Submit & Connect on WhatsApp", use_container_width=True):
                if l_name and l_phone:
                    row = pd.DataFrame([{"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"), "Name": l_name, "Phone": l_phone, "Interest": l_service, "Capital": l_cap}])
                    row.to_csv("kanira_option_leads.csv", mode="a", header=not os.path.exists("kanira_option_leads.csv"), index=False)
                    msg = f"Hello {BRAND_NAME}, I am {l_name} ({l_phone}). I submitted a request for *{l_service}* (Capital: {l_cap})."
                    st.success("Request saved! Click below to send directly on WhatsApp:")
                    st.markdown(f"[📲 Confirm on WhatsApp Now](https://wa.me{WHATSAPP_NO}?text={urllib.parse.quote(msg)})")
                else:
                    st.warning("Please enter both your Name and Mobile Number.")
    st.stop()

cur_user = st.session_state.auth_user
with st.sidebar:
    st.success(f"👤 {cur_user['name']} ({cur_user['role']})")
    if cur_user["role"] == "Advisor Admin" and os.path.exists("kanira_option_leads.csv"):
        with st.expander("📋 View Captured Client Leads"):
            ldf = pd.read_csv("kanira_option_leads.csv")
            st.dataframe(ldf, use_container_width=True, hide_index=True)
            st.download_button("⬇ Export Leads (.csv)", ldf.to_csv(index=False), "Kanira_Option_Leads.csv")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.auth_user = None
        st.rerun()
    st.divider()

import io, time
from datetime import date, timedelta
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from scipy.stats import norm

st.title("📈 2-Month Futures, Option Greeks, Time Value & Lot P&L Terminal")
st.caption("Near Month & Next Month Expiries • Calendar Spread • All 5 Greeks • Custom-Days 52W High/Low • Per-Lot Payoff & Excel Export")

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
        return {"fut": fut_px, "basis": basis, "c_px": c_intr, "p_px": p_intr, "c_intr": c_intr, "p_intr": p_intr,
                "c_tv": 0.0, "p_tv": 0.0, "c_delta": 1.0 if S > K else 0.0, "p_delta": -1.0 if S < K else 0.0,
                "gamma": 0.0, "c_theta": 0.0, "p_theta": 0.0, "vega": 0.0, "c_rho": 0.0, "p_rho": 0.0}

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

    return {"fut": fut_px, "basis": basis, "c_px": c_px, "p_px": p_px, "c_intr": c_intr, "p_intr": p_intr,
            "c_tv": max(0.0, c_px - c_intr), "p_tv": max(0.0, p_px - p_intr), "c_delta": c_delta, "p_delta": p_delta,
            "gamma": gamma, "c_theta": c_theta, "p_theta": p_theta, "vega": vega, "c_rho": c_rho, "p_rho": p_rho}

FNO_UNIVERSE = {
    "NIFTY 50 Index": ("^NSEI", 75, 50.0),
    "BANK NIFTY Index": ("^NSEBANK", 30, 100.0),
    "FINNIFTY Index": ("NIFTY_FIN_SERVICE.NS", 65, 50.0),
    "RELIANCE INDUSTRIES": ("RELIANCE.NS", 500, 10.0),
    "TCS": ("TCS.NS", 175, 20.0),
    "HDFC BANK": ("HDFCBANK.NS", 550, 10.0),
    "ICICI BANK": ("ICICIBANK.NS", 700, 10.0),
    "INFOSYS": ("INFY.NS", 400, 10.0),
    "STATE BANK OF INDIA": ("SBIN.NS", 750, 5.0),
    "LARSEN & TOUBRO": ("LT.NS", 150, 20.0),
    "BHARTI AIRTEL": ("BHARTIARTL.NS", 475, 10.0),
    "BAJAJ FINANCE": ("BAJFINANCE.NS", 125, 50.0),
    "TATA MOTORS": ("TATAMOTORS.NS", 550, 5.0),
    "SUN PHARMA": ("SUNPHARMA.NS", 350, 10.0),
    "MAHINDRA & MAHINDRA": ("M&M.NS", 350, 20.0),
    "Custom NSE F&O Symbol": ("CUSTOM", 250, 10.0)
}

@st.cache_data(ttl=60, show_spinner=False)
def fetch_live_fno(sym):
    hist = yf.Ticker(sym).history(period="1y")
    if hist.empty:
        raise ValueError("No market data returned")
    spot_v = float(hist["Close"].iloc[-1])
    h52_v = float(hist["High"].max())
    l52_v = float(hist["Low"].min())
    rets = np.log(hist["Close"] / hist["Close"].shift(1)).dropna().tail(30)
    hv_v = float(rets.std() * np.sqrt(252) * 100.0) if len(rets) > 5 else 18.0
    return round(spot_v, 2), round(h52_v, 2), round(l52_v, 2), round(max(8.0, min(hv_v, 95.0)), 1)

with st.sidebar:
    st.header("1. Live NSE F&O Stock / Index")
    fno_pick = st.selectbox("Select NSE F&O Underlying", list(FNO_UNIVERSE.keys()))
    def_sym, def_lot, step_sz = FNO_UNIVERSE[fno_pick]
    ticker = st.text_input("NSE Symbol", value="TATAPOWER.NS" if def_sym == "CUSTOM" else def_sym).strip().upper()
    if def_sym == "CUSTOM" and not ticker.endswith(".NS") and not ticker.startswith("^"):
        ticker = f"{ticker}.NS"

    live_sync = st.checkbox("Sync Live Spot, 52W Range & HV/IV", value=True)
    if st.button("🔄 Refresh Live NSE Price"):
        st.cache_data.clear()
        st.rerun()

    if live_sync:
        try:
            l_spot, l_h52, l_l52, l_iv = fetch_live_fno(ticker)
        except Exception as e:
            st.warning(f"Live feed fallback ({e})")
            l_spot, l_h52, l_l52, l_iv = 24150.0, 26277.0, 21281.0, 14.5
    else:
        l_spot, l_h52, l_l52, l_iv = 24150.0, 26277.0, 21281.0, 14.5

    st.header("2. Options Inputs (Spot, Strike, IV & Rate)")
    spot = st.number_input("Spot Price (S) [Editable]", value=float(l_spot), step=step_sz)
    atm_default = float(round(spot / step_sz) * step_sz)
    strike = st.number_input("Option Strike Price (K)", value=atm_default, step=step_sz)
    iv = st.slider("Implied Volatility (IV %)", 5.0, 100.0, float(l_iv), 0.5) / 100.0
    r = st.number_input("Risk-Free Interest Rate (%)", value=6.75, step=0.25) / 100.0
    q = st.number_input("Dividend Yield (%)", value=1.20, step=0.10) / 100.0

    st.header("3. Expiry & Position Sizing")
    exp_map = {"Thursday (Nifty / Stock F&O)": 3, "Wednesday (Bank Nifty)": 2, "Tuesday (FinNifty)": 1}
    exp_lbl = st.selectbox("Monthly Expiry Day", list(exp_map.keys()))
    exp_day = exp_map[exp_lbl]
    lot_size = st.number_input("Contract Lot Size", min_value=1, value=int(def_lot), step=5)
    num_lots = st.number_input("Number of Lots", min_value=1, value=1, step=1)
    side = st.radio("Position Direction", ["Buy (Long)", "Sell (Short)"], horizontal=True)
    high_52 = st.number_input("52-Week High (₹)", value=float(l_h52), step=step_sz)
    low_52 = st.number_input("52-Week Low (₹)", value=float(l_l52), step=step_sz)
    auto_refresh = st.checkbox("Auto-Refresh Live Every 15s", value=False)

qty = lot_size * num_lots
sign = 1 if side == "Buy (Long)" else -1
expiries = get_two_month_expiries(exp_day)

rows = []
for label, dte in expiries:
    res = calc_derivatives(spot, strike, dte / 365.0, r, q, iv)
    rows.append({
        "2-Month Contract": label, "DTE": dte,
        "Futures Fair Value (₹)": round(res["fut"], 2), "Basis / Carry (₹)": round(res["basis"], 2),
        "Lot Contract Value (₹)": round(res["fut"] * qty, 0),
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
c1.metric(f"{ticker} Spot Price (S)", f"₹ {spot:,.2f}", f"Strike: ₹{strike:,.0f} | IV: {iv*100:.1f}%")
c2.metric("1st Month Futures", f"₹ {df.loc[0, 'Futures Fair Value (₹)']:,.2f}", f"Carry: +₹ {df.loc[0, 'Basis / Carry (₹)']:,.2f}")
c3.metric("2nd Month Futures", f"₹ {df.loc[1, 'Futures Fair Value (₹)']:,.2f}", f"Carry: +₹ {df.loc[1, 'Basis / Carry (₹)']:,.2f}")
c4.metric("2-Month Calendar Spread", f"₹ {cal_spread:,.2f}", f"Qty: {qty:,} ({num_lots} Lot)")
st.progress(min(max(range_pct / 100.0, 0.0), 1.0))

st.divider()
st.subheader(f"⏳ Time Value, Custom-Days 52-Week High/Low & Lot P&L ({side} • {qty:,} Qty)")

sc1, sc2 = st.columns([1, 2.3])
with sc1:
    selected_idx = st.selectbox("Select 2-Month Contract", [0, 1], format_func=lambda i: expiries[i][0])
    contract_dte = expiries[selected_idx][1]
    days_elapsed = st.slider("Custom Days Elapsed to Reach Target", 0, contract_dte, min(5, contract_dte))
    rem_dte = max(0, contract_dte - days_elapsed)
    entry = calc_derivatives(spot, strike, contract_dte / 365.0, r, q, iv)
    st.info(f"**Contract DTE:** {contract_dte} days  \n**Days Elapsed:** {days_elapsed} days  \n**Remaining DTE:** {rem_dte} days  \n**Entry Call:** ₹{entry['c_px']:,.2f} | **Entry Put:** ₹{entry['p_px']:,.2f}")

with sc2:
    T_rem = rem_dte / 365.0
    scenarios = [
        (f"Current Spot (₹ {spot:,.0f})", spot),
        (f"52-Week High (₹ {high_52:,.0f})", high_52),
        (f"52-Week Low (₹ {low_52:,.0f})", low_52)
    ]
    scen_rows = []
    for s_name, s_px in scenarios:
        val = calc_derivatives(s_px, strike, T_rem, r, q, iv)
        scen_rows.append({
            "Scenario": s_name,
            "Fut Price (₹)": round(val["fut"], 2),
            "Fut P&L / Lot (₹)": round(sign * (val["fut"] - entry["fut"]) * qty, 0),
            "CALL Prem (₹)": round(val["c_px"], 2),
            "CALL Time Val": round(val["c_tv"], 2),
            "CALL P&L / Lot (₹)": round(sign * (val["c_px"] - entry["c_px"]) * qty, 0),
            "PUT Prem (₹)": round(val["p_px"], 2),
            "PUT Time Val": round(val["p_tv"], 2),
            "PUT P&L / Lot (₹)": round(sign * (val["p_px"] - entry["p_px"]) * qty, 0)
        })
    scen_df = pd.DataFrame(scen_rows)
    st.dataframe(scen_df, use_container_width=True, hide_index=True)

st.subheader(f"📉 Interactive Payoff Curve Across 52-Week Range (After {days_elapsed} Days • {qty:,} Qty)")
grid_prices = np.linspace(low_52 * 0.98, high_52 * 1.02, 45)
call_pnls, put_pnls, fut_pnls = [], [], []
for gp in grid_prices:
    v = calc_derivatives(gp, strike, T_rem, r, q, iv)
    call_pnls.append(sign * (v["c_px"] - entry["c_px"]) * qty)
    put_pnls.append(sign * (v["p_px"] - entry["p_px"]) * qty)
    fut_pnls.append(sign * (v["fut"] - entry["fut"]) * qty)

fig = go.Figure()
fig.add_trace(go.Scatter(x=grid_prices, y=call_pnls, mode="lines", name="CALL P&L (₹)", line=dict(color="#10b981", width=2.2)))
fig.add_trace(go.Scatter(x=grid_prices, y=put_pnls, mode="lines", name="PUT P&L (₹)", line=dict(color="#ef4444", width=2.2)))
fig.add_trace(go.Scatter(x=grid_prices, y=fut_pnls, mode="lines", name="Futures P&L (₹)", line=dict(color="#3b82f6", width=1.8, dash="dot")))
fig.add_hline(y=0, line_color="#94a3b8", line_dash="dash")
fig.add_vline(x=strike, line_color="#f59e0b", line_dash="dot", annotation_text=f"Strike: ₹{strike:,.0f}")
fig.update_layout(height=380, template="plotly_white", xaxis_title="Underlying Spot Price (₹)", yaxis_title="Net P&L per Position (₹)", margin=dict(l=10, r=10, t=20, b=10))
st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("📊 2-Month Futures, Intrinsic/Time Value & All 5 Option Greeks")
st.dataframe(df, use_container_width=True, hide_index=True)

xl_buf = io.BytesIO()
with pd.ExcelWriter(xl_buf, engine="openpyxl") as writer:
    df.to_excel(writer, sheet_name="2M_Futures_and_Greeks", index=False)
    scen_df.to_excel(writer, sheet_name="52W_Custom_Days_PnL", index=False)
st.download_button("⬇ Download 2-Month Futures, Greeks & P&L Report (.xlsx)", xl_buf.getvalue(), f"{ticker}_2M_Derivatives_Report.xlsx")

if auto_refresh:
    time.sleep(5)
    st.rerun()
