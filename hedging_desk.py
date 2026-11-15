import numpy as np
import pandas as pd
import streamlit as st
from scipy.stats import norm

st.set_page_config(page_title="Kanira Advisor | HNI Covered Call & Collar Hedging Desk", layout="wide")
st.title("🛡️ Kanira Advisor — HNI Covered Call & Protective Collar Hedging Desk")
st.caption("Generate monthly option yield on Demat stock holdings or lock in downside protection without triggering capital gains tax.")

def bs_price(S, K, T, r, sigma, opt_type="call"):
    if T <= 0:
        return max(0.0, S - K) if opt_type == "call" else max(0.0, K - S)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if opt_type == "call":
        return float(S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2))
    return float(K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1))

with st.sidebar:
    st.header("1. HNI Stock / Portfolio Holding")
    stock_name = st.text_input("Stock / Index Name", value="RELIANCE / NIFTY")
    spot = st.number_input("Current Spot Price (Rs.)", value=1350.0, step=10.0)
    lot_size = st.number_input("F&O Lot Size", min_value=1, value=500, step=25)
    num_lots = st.number_input("Number of Lots Held", min_value=1, value=4, step=1)
    days = st.slider("Days to Monthly Expiry", 1, 60, 25)
    iv = st.slider("Implied Volatility (IV %)", 8.0, 80.0, 22.0, 0.5) / 100.0
    r = st.number_input("Risk-Free Rate (%)", value=6.75, step=0.25) / 100.0

    st.header("2. Hedging Strikes")
    strategy = st.selectbox("Select Hedging Strategy", ["Covered Call (Yield Generation)", "Zero-Cost / Protective Collar (Downside Floor)", "Protective Put (Crash Insurance)"])
    call_strike = st.number_input("Sell OTM Call Strike (Cap)", value=float(round(spot * 1.04 / 10) * 10), step=10.0)
    put_strike = st.number_input("Buy OTM Put Strike (Floor)", value=float(round(spot * 0.96 / 10) * 10), step=10.0)

qty = lot_size * num_lots
holding_val = spot * qty
T = days / 365.0

call_prem = bs_price(spot, call_strike, T, r, iv, "call")
put_prem = bs_price(spot, put_strike, T, r, iv, "put")

if strategy == "Covered Call (Yield Generation)":
    net_prem_unit = call_prem
    breakeven = spot - net_prem_unit
    max_profit = ((call_strike - spot) + net_prem_unit) * qty
    max_loss = "Unlimited below Breakeven (Cushioned by Call Premium)"
elif strategy == "Zero-Cost / Protective Collar (Downside Floor)":
    net_prem_unit = call_prem - put_prem
    breakeven = spot - net_prem_unit
    max_profit = ((call_strike - spot) + net_prem_unit) * qty
    max_loss = f"Rs. {abs(((put_strike - spot) + net_prem_unit) * qty):,.0f} (Locked Floor at Rs. {put_strike:,.0f})"
else:
    net_prem_unit = -put_prem
    breakeven = spot + put_prem
    max_profit = "Unlimited Upside (Minus Put Cost)"
    max_loss = f"Rs. {abs(((put_strike - spot) - put_prem) * qty):,.0f} (Locked Floor at Rs. {put_strike:,.0f})"

net_cashflow = net_prem_unit * qty
yield_pct = (net_cashflow / holding_val) * 100.0
ann_yield = yield_pct * (365.0 / max(days, 1))

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Holding Value", f"Rs. {holding_val:,.0f}", f"{qty:,} Shares ({num_lots} Lots)")
m2.metric("Net Option Cashflow", f"Rs. {net_cashflow:,.0f}", f"{yield_pct:+.2f}% ({ann_yield:+.1f}% Ann.)")
m3.metric("Effective Breakeven", f"Rs. {breakeven:,.2f}", f"Call: Rs.{call_prem:.2f} | Put: Rs.{put_prem:.2f}")
m4.metric("Max Upside Profit", f"Rs. {max_profit:,.0f}" if isinstance(max_profit, float) else "Uncapped", f"Floor: Rs. {put_strike:,.0f}")

st.info(f"**Strategy Risk Profile:** Max Downside Risk = **{max_loss}**")

prices = np.linspace(spot * 0.85, spot * 1.15, 35)
rows = []
for p in prices:
    unhedged = (p - spot) * qty
    if strategy == "Covered Call (Yield Generation)":
        hedged = unhedged + (call_prem - max(0.0, p - call_strike)) * qty
    elif strategy == "Zero-Cost / Protective Collar (Downside Floor)":
        hedged = unhedged + (call_prem - max(0.0, p - call_strike) + max(0.0, put_strike - p) - put_prem) * qty
    else:
        hedged = unhedged + (max(0.0, put_strike - p) - put_prem) * qty
    rows.append({"Expiry Stock Price": round(p, 1), "Unhedged Stock P&L (Rs.)": round(unhedged), "Hedged Strategy P&L (Rs.)": round(hedged)})

pay_df = pd.DataFrame(rows)
st.subheader(f"📉 Expiry Payoff Comparison: Unhedged vs. {strategy}")
st.line_chart(pay_df.set_index("Expiry Stock Price"))

st.subheader("📋 Expiry Scenario Breakdown Table")
key_prices = [round(spot * m, 1) for m in [0.90, 0.95, 1.00, 1.04, 1.08]]
scen_rows = []
for kp in key_prices:
    unh = (kp - spot) * qty
    if strategy == "Covered Call (Yield Generation)":
        hdg = unh + (call_prem - max(0.0, kp - call_strike)) * qty
    elif strategy == "Zero-Cost / Protective Collar (Downside Floor)":
        hdg = unh + (call_prem - max(0.0, kp - call_strike) + max(0.0, put_strike - kp) - put_prem) * qty
    else:
        hdg = unh + (max(0.0, put_strike - kp) - put_prem) * qty
    scen_rows.append({"Expiry Price (Rs.)": kp, "Move %": f"{((kp-spot)/spot)*100:+.1f}%", "Unhedged P&L (Rs.)": round(unh), "Hedged P&L (Rs.)": round(hdg), "Hedge Advantage (Rs.)": round(hdg - unh)})
st.dataframe(pd.DataFrame(scen_rows), use_container_width=True, hide_index=True)
