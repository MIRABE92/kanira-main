import io
from datetime import date
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Kanira Advisor | HNI Private Wealth & Stress-Test Suite", layout="wide")
st.title("🏛️ Kanira Advisor — HNI Private Wealth, Stress-Test & Tax Harvesting Suite")
st.caption("Institutional Family-Office Analytics: Market Crash Stress Testing, XIRR Computation & Capital Gains Tax Harvesting.")

STRESS_SCENARIOS = {
    "2020 COVID Flash Crash (-35% Equity, +12% Gold, +4% Debt)": {"Equity": -0.35, "Global": -0.30, "Debt": 0.04, "Gold": 0.12},
    "2008 Global Financial Crisis (-52% Equity, +18% Gold, +6% Debt)": {"Equity": -0.52, "Global": -0.48, "Debt": 0.06, "Gold": 0.18},
    "Rate Hike & Stagflation (-18% Equity, -6% Debt, +10% Gold)": {"Equity": -0.18, "Global": -0.20, "Debt": -0.06, "Gold": 0.10},
    "Bull Market Rally (+28% Equity, +25% Global, +7% Debt)": {"Equity": 0.28, "Global": 0.25, "Debt": 0.07, "Gold": 0.05}
}

def calc_xirr(cashflows, dates):
    if len(cashflows) < 2 or not (any(c < 0 for c in cashflows) and any(c > 0 for c in cashflows)):
        return 0.0
    d0 = min(dates)
    years = np.array([(d - d0).days / 365.0 for d in dates], dtype=float)
    cf = np.array(cashflows, dtype=float)
    rate = 0.12
    for _ in range(100):
        f = np.sum(cf / ((1.0 + rate) ** years))
        df = np.sum(-years * cf / ((1.0 + rate) ** (years + 1.0)))
        if abs(df) < 1e-9:
            break
        new_rate = rate - f / df
        if abs(new_rate - rate) < 1e-7:
            return round(new_rate * 100, 2)
        rate = max(-0.95, min(new_rate, 10.0))
    return round(rate * 100, 2)

t1, t2, t3 = st.tabs(["1. Portfolio Crash Stress-Test", "2. Tax-Loss Harvesting Scanner", "3. Exact Family XIRR Calculator"])

with t1:
    st.subheader("Institutional Tail-Risk & Market Crash Simulator")
    c1, c2, c3, c4 = st.columns(4)
    eq_val = c1.number_input("Indian Equity Value (Rs.)", value=3500000, step=100000)
    gl_val = c2.number_input("Global Equity Value (Rs.)", value=1000000, step=100000)
    db_val = c3.number_input("Debt & Bonds Value (Rs.)", value=1500000, step=100000)
    gd_val = c4.number_input("Gold / SGB Value (Rs.)", value=500000, step=50000)

    tot_port = eq_val + gl_val + db_val + gd_val
    scen_name = st.selectbox("Select Historical / Macro Stress Scenario", list(STRESS_SCENARIOS.keys()))
    shocks = STRESS_SCENARIOS[scen_name]

    post_eq = eq_val * (1 + shocks["Equity"])
    post_gl = gl_val * (1 + shocks["Global"])
    post_db = db_val * (1 + shocks["Debt"])
    post_gd = gd_val * (1 + shocks["Gold"])
    post_tot = post_eq + post_gl + post_db + post_gd
    drawdown = post_tot - tot_port

    m1, m2, m3 = st.columns(3)
    m1.metric("Current HNI Portfolio", f"Rs. {tot_port:,.0f}")
    m2.metric("Stressed Portfolio Value", f"Rs. {post_tot:,.0f}", f"Rs. {drawdown:,.0f}")
    m3.metric("Portfolio Drawdown (%)", f"{(drawdown / tot_port * 100):.2f}%" if tot_port else "0%", "Max Loss Impact")

    comp_df = pd.DataFrame([
        {"Asset Class": "Indian Equity", "Current (Rs.)": eq_val, "Stressed (Rs.)": round(post_eq)},
        {"Asset Class": "Global Equity", "Current (Rs.)": gl_val, "Stressed (Rs.)": round(post_gl)},
        {"Asset Class": "Debt & Bonds", "Current (Rs.)": db_val, "Stressed (Rs.)": round(post_db)},
        {"Asset Class": "Gold / SGB", "Current (Rs.)": gd_val, "Stressed (Rs.)": round(post_gd)}
    ])
    st.bar_chart(comp_df.set_index("Asset Class"))

with t2:
    st.subheader("Capital Gains & Tax-Loss Harvesting Scanner (FY End Optimization)")
    st.info("Enter or upload holdings with Buy Value, Current Value, and Holding Period (>12 months = LTCG, <=12 months = STCG) to identify tax-saving sell/switch candidates.")
    tax_sample = pd.DataFrame([
        {"Stock_or_Fund": "Nifty Large Cap Fund", "Buy_Value": 800000, "Current_Value": 1040000, "Months_Held": 18},
        {"Stock_or_Fund": "Midcap Opportunities Fund", "Buy_Value": 600000, "Current_Value": 525000, "Months_Held": 8},
        {"Stock_or_Fund": "IT Sector ETF", "Buy_Value": 400000, "Current_Value": 340000, "Months_Held": 15},
        {"Stock_or_Fund": "Pharma Direct Stock", "Buy_Value": 500000, "Current_Value": 610000, "Months_Held": 9}
    ])
    t_df = st.data_editor(tax_sample, num_rows="dynamic", use_container_width=True)
    t_df["Unrealized_PnL"] = t_df["Current_Value"] - t_df["Buy_Value"]
    t_df["Tax_Bucket"] = t_df["Months_Held"].apply(lambda m: "LTCG (>12m)" if m > 12 else "STCG (<=12m)")
    t_df["Harvest_Action"] = t_df["Unrealized_PnL"].apply(lambda p: "Harvest Loss (Book & Reinvest)" if p < -10000 else ("Exempt LTCG Buffer" if p > 0 else "Hold"))

    stcg_gains = t_df[(t_df["Tax_Bucket"] == "STCG (<=12m)") & (t_df["Unrealized_PnL"] > 0)]["Unrealized_PnL"].sum()
    harvestable_loss = abs(t_df[t_df["Unrealized_PnL"] < 0]["Unrealized_PnL"].sum())
    est_tax_saved = min(stcg_gains, harvestable_loss) * 0.20

    k1, k2, k3 = st.columns(3)
    k1.metric("Unrealized STCG Gains", f"Rs. {stcg_gains:,.0f}")
    k2.metric("Harvestable Tax Losses", f"Rs. {harvestable_loss:,.0f}")
    k3.metric("Est. Tax Offset Savings (20% STCG)", f"Rs. {est_tax_saved:,.0f}")
    st.dataframe(t_df, use_container_width=True, hide_index=True)

with t3:
    st.subheader("Exact Irregular Cash-Flow XIRR Calculator")
    cf_sample = pd.DataFrame([
        {"Date": "2024-04-10", "Cashflow_Rs": -500000, "Note": "Initial Lumpsum"},
        {"Date": "2024-10-15", "Cashflow_Rs": -250000, "Note": "Top-up Investment"},
        {"Date": "2025-06-20", "Cashflow_Rs": -300000, "Note": "Second Top-up"},
        {"Date": "2026-11-15", "Cashflow_Rs": 1365000, "Note": "Current Portfolio Valuation"}
    ])
    cf_df = st.data_editor(cf_sample, num_rows="dynamic", use_container_width=True)
    if st.button("Calculate Portfolio XIRR", type="primary"):
        dates_list = [pd.to_datetime(d).date() for d in cf_df["Date"]]
        vals_list = [float(v) for v in cf_df["Cashflow_Rs"]]
        xirr_val = calc_xirr(vals_list, dates_list)
        st.success(f"Annualized Portfolio XIRR: **{xirr_val}% p.a.**")
