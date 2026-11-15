import io
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Kanira Advisor | Portfolio Rating & Wealth Builder", layout="wide")
st.title("Kanira Advisor - Portfolio Rating & Wealth Builder")
st.caption("Evaluate existing client holdings (0-100 Health Score), generate rebalancing trades, and build goal-based portfolios.")

SAMPLE_HOLDINGS = pd.DataFrame([
    {"Asset_Name": "Nifty 50 Index / Large Cap Equity", "Category": "Equity", "Invested_Value": 450000, "Current_Value": 540000, "Expected_Return_Pct": 12.5, "Expense_Ratio_Pct": 0.25},
    {"Asset_Name": "Flexi Cap & Mid Cap Funds", "Category": "Equity", "Invested_Value": 300000, "Current_Value": 375000, "Expected_Return_Pct": 14.5, "Expense_Ratio_Pct": 0.85},
    {"Asset_Name": "Reliance / Direct Stock Allocation", "Category": "Equity", "Invested_Value": 250000, "Current_Value": 310000, "Expected_Return_Pct": 13.5, "Expense_Ratio_Pct": 0.00},
    {"Asset_Name": "Short Duration Debt / Liquid Fund", "Category": "Debt", "Invested_Value": 200000, "Current_Value": 218000, "Expected_Return_Pct": 7.2, "Expense_Ratio_Pct": 0.35},
    {"Asset_Name": "Sovereign Gold Bond / Gold ETF", "Category": "Gold", "Invested_Value": 100000, "Current_Value": 128000, "Expected_Return_Pct": 9.0, "Expense_Ratio_Pct": 0.50},
    {"Asset_Name": "Global US Tech / S&P 500 (GIFT City)", "Category": "Global", "Invested_Value": 100000, "Current_Value": 129000, "Expected_Return_Pct": 13.0, "Expense_Ratio_Pct": 0.65}
])

def rate_portfolio(df):
    total_val = df["Current_Value"].sum()
    if total_val <= 0:
        return 0, "N/A", {}, df
    df = df.copy()
    df["Weight_%"] = (df["Current_Value"] / total_val * 100).round(2)
    df["Gain_%"] = ((df["Current_Value"] - df["Invested_Value"]) / df["Invested_Value"].replace(0, np.nan) * 100).fillna(0).round(2)
    div_score = min(30, df["Category"].nunique() * 7.5)
    max_w = df["Weight_%"].max()
    conc_score = 30 if max_w <= 25 else max(5, 30 - (max_w - 25) * 1.2)
    w_ret = (df["Weight_%"] / 100 * df["Expected_Return_Pct"]).sum()
    ret_score = min(25, max(8, (w_ret - 6) * 3.2))
    w_exp = (df["Weight_%"] / 100 * df["Expense_Ratio_Pct"]).sum()
    cost_score = 15 if w_exp <= 0.6 else max(4, 15 - (w_exp - 0.6) * 8)
    total_score = int(round(div_score + conc_score + ret_score + cost_score))
    grade = "A+ (Optimal)" if total_score >= 85 else ("B+ (Balanced)" if total_score >= 70 else ("C (Needs Rebalancing)" if total_score >= 55 else "D (High Concentration Risk)"))
    metrics = {"score": total_score, "grade": grade, "w_ret": round(w_ret, 2), "w_exp": round(w_exp, 2), "max_w": round(max_w, 1), "total_val": total_val, "total_inv": df["Invested_Value"].sum()}
    return total_score, grade, metrics, df

tab1, tab2 = st.tabs(["1. Existing Portfolio Rating & Rebalancer", "2. Build New Goal-Based Portfolio"])

with tab1:
    c_up1, c_up2 = st.columns([1.2, 2])
    with c_up1:
        tpl_buf = io.BytesIO()
        SAMPLE_HOLDINGS.to_excel(tpl_buf, index=False)
        st.download_button("Download Portfolio Template (.xlsx)", tpl_buf.getvalue(), "Client_Portfolio_Template.xlsx")
        up_port = st.file_uploader("Upload Client Holdings (.xlsx or .csv)", type=["xlsx", "xls", "csv"])
    with c_up2:
        st.info("Edit holdings directly in the table below or upload a client Excel/CSV portfolio to compute live ratings and rebalancing actions.")

    raw_df = (pd.read_csv(up_port) if up_port.name.lower().endswith(".csv") else pd.read_excel(up_port)) if up_port else SAMPLE_HOLDINGS
    edited_df = st.data_editor(raw_df, num_rows="dynamic", use_container_width=True)

    score, grade, meta, rated_df = rate_portfolio(edited_df)
    if meta:
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Portfolio Health Rating", f"{score} / 100", grade)
        m2.metric("Current Value", f"Rs. {meta['total_val']:,.0f}", f"Gain: Rs. {meta['total_val'] - meta['total_inv']:,.0f}")
        m3.metric("Expected CAGR", f"{meta['w_ret']}%", "Weighted Return")
        m4.metric("Top Holding Weight", f"{meta['max_w']}%", "Ideal <= 25%")
        m5.metric("Avg Expense Drag", f"{meta['w_exp']}%", "Ideal <= 0.60%")
        st.progress(min(max(score / 100.0, 0.0), 1.0))

        ch1, ch2 = st.columns(2)
        with ch1:
            st.subheader("Asset Allocation Breakdown")
            st.bar_chart(rated_df.groupby("Category")["Current_Value"].sum())
        with ch2:
            st.subheader("Rebalancing Action Plan")
            rated_df["Suggested_Action"] = rated_df["Weight_%"].apply(lambda w: "Trim Overweight (>25%)" if w > 25 else ("Accumulate / SIP" if w < 12 else "Hold (Optimal)"))
            st.dataframe(rated_df[["Asset_Name", "Category", "Current_Value", "Weight_%", "Gain_%", "Suggested_Action"]], use_container_width=True, hide_index=True)

        rep_buf = io.BytesIO()
        with pd.ExcelWriter(rep_buf, engine="openpyxl") as writer:
            rated_df.to_excel(writer, sheet_name="Rated_Portfolio", index=False)
            pd.DataFrame([meta]).to_excel(writer, sheet_name="Health_Summary", index=False)
        st.download_button("Download Client Portfolio Rating Report (.xlsx)", rep_buf.getvalue(), "Kanira_Portfolio_Rating_Report.xlsx")

with tab2:
    st.subheader("Build a Custom Model Portfolio & Wealth Projection")
    b1, b2, b3 = st.columns(3)
    client_name = b1.text_input("Client Name", value="Investor")
    risk_profile = b1.selectbox("Client Risk Profile", ["Balanced Growth (12.5% CAGR)", "Aggressive Wealth (14.5% CAGR)", "Conservative Income (9.0% CAGR)"])
    lump_sum = b2.number_input("Initial Lumpsum Investment (Rs.)", value=500000, step=50000)
    monthly_sip = b2.number_input("Monthly SIP Contribution (Rs.)", value=25000, step=2500)
    horizon_yrs = b3.slider("Investment Horizon (Years)", 3, 30, 15)
    step_up = b3.slider("Annual SIP Step-Up (%)", 0, 20, 10)

    alloc_map = {
        "Balanced Growth (12.5% CAGR)": (0.125, {"Large & Flexi Cap Equity": 45, "Mid & Small Cap Equity": 20, "Debt / Corporate Bonds": 20, "Gold / SGBs": 10, "Global US Equity (GIFT City)": 5}),
        "Aggressive Wealth (14.5% CAGR)": (0.145, {"Large & Flexi Cap Equity": 40, "Mid & Small Cap Equity": 35, "Global US Equity (GIFT City)": 15, "Gold / SGBs": 5, "Debt / Liquid": 5}),
        "Conservative Income (9.0% CAGR)": (0.090, {"Debt / Corporate Bonds": 50, "Large Cap Index Equity": 25, "Gold / SGBs": 15, "Arbitrage / Liquid": 10})
    }
    exp_r, weights = alloc_map[risk_profile]

    yr_rows, corpus, total_invested, cur_sip = [], float(lump_sum), float(lump_sum), float(monthly_sip)
    m_rate = exp_r / 12.0
    for y in range(1, horizon_yrs + 1):
        for _ in range(12):
            corpus = (corpus + cur_sip) * (1 + m_rate)
            total_invested += cur_sip
        yr_rows.append({"Year": f"Year {y}", "Total Invested (Rs.)": round(total_invested), "Projected Value (Rs.)": round(corpus)})
        cur_sip *= (1 + step_up / 100.0)

    proj_df = pd.DataFrame(yr_rows)
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Amount Invested", f"Rs. {total_invested:,.0f}")
    k2.metric(f"Projected Corpus ({horizon_yrs} Yrs)", f"Rs. {corpus:,.0f}", f"Wealth Gain: Rs. {corpus - total_invested:,.0f}")
    k3.metric("Recommended Monthly Split", f"Rs. {monthly_sip:,.0f} / mo", "Target Plan")

    bc1, bc2 = st.columns([1, 1.5])
    with bc1:
        st.markdown("**Recommended Asset Allocation**")
        alloc_df = pd.DataFrame([{"Asset Class": k, "Weight (%)": v, "Lumpsum (Rs.)": round(lump_sum * v / 100), "Monthly SIP (Rs.)": round(monthly_sip * v / 100)} for k, v in weights.items()])
        st.dataframe(alloc_df, use_container_width=True, hide_index=True)
    with bc2:
        st.markdown("**Wealth Compounding Trajectory**")
        st.area_chart(proj_df.set_index("Year")[["Total Invested (Rs.)", "Projected Value (Rs.)"]])
