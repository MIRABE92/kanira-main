import io
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Kanira Advisor | NSE Positional, Multi-TF RSI & Ownership Terminal", layout="wide")
st.title("🇮🇳 NSE Positional, Editable P/E & PEG, Multi-Timeframe RSI & Ownership Terminal")
st.caption("INR (₹ / ₹ Cr) • 200/63/14 MAs • 15m/1h/1D/1W RSI • 1M Avg Volume & Delivery • FII/DII/Retail Value.")

NSE_POPULAR = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "BHARTIARTL.NS",
    "SBIN.NS", "LT.NS", "ITC.NS", "HINDUNILVR.NS", "BAJFINANCE.NS", "SUNPHARMA.NS",
    "TATAMOTORS.NS", "M&M.NS", "MARUTI.NS", "NTPC.NS", "POWERGRID.NS", "TITAN.NS",
    "ASIANPAINT.NS", "ADANIENT.NS", "ADANIPORTS.NS", "ULTRACEMCO.NS", "JSWSTEEL.NS",
    "TATASTEEL.NS", "HINDALCO.NS", "TRENT.NS", "BEL.NS", "HAL.NS", "ZOMATO.NS", "DLF.NS"
]

def calc_rsi_series(close_s, period=14):
    if close_s is None or len(close_s) < period + 2:
        return 50.0
    delta = close_s.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    val = rsi.iloc[-1]
    return round(float(val), 1) if pd.notna(val) else 50.0

@st.cache_data(ttl=300, show_spinner=False)
def sync_nse_full(sym):
    tk = yf.Ticker(sym)
    hist = tk.history(period="1y")
    nifty = yf.Ticker("^NSEI").history(period="1y")
    info = tk.info or {}
    fin, bs = tk.financials, tk.balance_sheet

    # Multi-timeframe RSI (15m, 1h, 1D, 1W)
    h_15m = tk.history(period="15d", interval="15m")
    h_1h = tk.history(period="60d", interval="1h")
    rsi_15m = calc_rsi_series(h_15m["Close"]) if not h_15m.empty else 50.0
    rsi_1h = calc_rsi_series(h_1h["Close"]) if not h_1h.empty else 50.0
    rsi_1d = calc_rsi_series(hist["Close"]) if not hist.empty else 50.0
    wk_close = hist["Close"].resample("W").last() if not hist.empty else pd.Series(dtype=float)
    rsi_1w = calc_rsi_series(wk_close) if len(wk_close) > 15 else rsi_1d

    def gv(df, keys, default):
        if df is not None and not df.empty:
            for k in keys:
                if k in df.index and pd.notna(df.loc[k].iloc[0]):
                    return abs(float(df.loc[k].iloc[0])) / 1e7
        return default

    cmp = float(hist["Close"].iloc[-1]) if not hist.empty else float(info.get("currentPrice") or 1500.0)
    shares_cr = float(info.get("sharesOutstanding") or (100000e7 / max(cmp, 1.0))) / 1e7
    prom_pct = round(float(info.get("heldPercentInsiders") or 0.50) * 100.0, 1)
    inst_pct = round(float(info.get("heldPercentInstitutions") or 0.30) * 100.0, 1)
    fii_est = round(inst_pct * 0.55, 1)
    dii_est = round(inst_pct * 0.45, 1)

    eps = float(info.get("trailingEps") or max(cmp / 25.0, 5.0))
    eps_g = float(info.get("earningsGrowth") or 0.16) * 100.0
    if eps_g <= 0:
        eps_g = 15.0
    rev = gv(fin, ["Total Revenue", "Operating Revenue"], 45000.0)
    ebit = gv(fin, ["EBIT", "Operating Income"], rev * 0.18)
    int_exp = gv(fin, ["Interest Expense", "Interest Expense Non Operating"], 450.0)
    pat = gv(fin, ["Net Income", "Net Income Common Stockholders"], ebit * 0.72)
    assets = gv(bs, ["Total Assets"], 65000.0)
    equity = gv(bs, ["Stockholders Equity", "Total Equity Gross Minority Interest"], 32000.0)
    debt = gv(bs, ["Total Debt", "Long Term Debt"], 8000.0)
    cl = gv(bs, ["Current Liabilities"], assets * 0.22)

    data = {
        "cmp": round(cmp, 2), "shares_cr": round(shares_cr, 2), "prom_pct": prom_pct,
        "fii_pct": fii_est, "dii_pct": dii_est, "eps": round(eps, 2), "eps_g": round(eps_g, 1),
        "rev": round(rev, 1), "ebit": round(ebit, 1), "int_exp": round(int_exp, 1),
        "pat": round(pat, 1), "assets": round(assets, 1), "equity": round(equity, 1),
        "debt": round(debt, 1), "cl": round(cl, 1),
        "rsi_15m": rsi_15m, "rsi_1h": rsi_1h, "rsi_1d": rsi_1d, "rsi_1w": rsi_1w
    }
    return hist, nifty, data

def run_nse_calculations(hist, nifty, p):
    df = hist.copy()
    df["MA14"] = df["Close"].ewm(span=14, adjust=False).mean()
    df["MA63"] = df["Close"].rolling(63).mean()
    df["MA200"] = df["Close"].rolling(200).mean()

    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - df["Close"].shift()).abs(),
        (df["Low"] - df["Close"].shift()).abs()
    ], axis=1).max(axis=1)
    df["ATR14"] = tr.rolling(14).mean()

    cmp = p["cmp"]
    atr = float(df["ATR14"].iloc[-1]) if (not df.empty and pd.notna(df["ATR14"].iloc[-1])) else cmp * 0.02

    # 1-Month (21 Trading Days) Average Volume & Delivery/Demat Value in INR
    vol_1m_avg = float(df["Volume"].tail(21).mean()) if not df.empty else 0.0
    vol_last = float(df["Volume"].iloc[-1]) if not df.empty else 0.0
    vol_surge = vol_last / max(vol_1m_avg, 1.0)
    deliv_shares_1m = vol_1m_avg * (p["deliv_pct"] / 100.0)
    deliv_val_1m_cr = (deliv_shares_1m * cmp) / 1e7

    # Outstanding Shares & Ownership Value Split (INR Crores)
    tot_mcap_cr = p["shares_cr"] * cmp
    retail_pct = max(0.0, round(100.0 - (p["prom_pct"] + p["fii_pct"] + p["dii_pct"]), 2))
    prom_val_cr = tot_mcap_cr * (p["prom_pct"] / 100.0)
    fii_val_cr = tot_mcap_cr * (p["fii_pct"] / 100.0)
    dii_val_cr = tot_mcap_cr * (p["dii_pct"] / 100.0)
    retail_val_cr = tot_mcap_cr * (retail_pct / 100.0)

    # 3-Month (63-Day) Relative Strength vs Nifty 50
    lb = min(63, len(df) - 1, len(nifty) - 1)
    rs_alpha = (((df["Close"].iloc[-1] / df["Close"].iloc[-1 - lb]) - 1) - ((nifty["Close"].iloc[-1] / nifty["Close"].iloc[-1 - lb]) - 1)) * 100 if lb > 0 else 0.0

    # Positional Stop-Loss, Target & Sizing in INR
    sl_px = max(0.1, cmp - atr * p["atr_mult"])
    risk_unit = max(0.1, cmp - sl_px)
    tech_target = cmp + risk_unit * p["rr"]
    max_risk_inr = p["capital"] * (p["risk_pct"] / 100.0)
    qty = int(max_risk_inr // risk_unit)
    pos_val = qty * cmp

    # Current vs Edited P/E & PEG Fair Price Derivation
    curr_pe = cmp / max(p["eps"], 0.1)
    curr_peg = curr_pe / max(p["eps_g"], 0.5)
    fwd_eps = p["eps"] * (1.0 + p["eps_g"] / 100.0)
    fair_px_by_pe = fwd_eps * p["edit_pe"]
    fair_px_by_peg = fwd_eps * (p["edit_peg"] * p["eps_g"])
    blended_fair_px = (fair_px_by_pe + fair_px_by_peg) / 2.0

    # ROE, ROCE, Debt Rate & Asset Quality (INR Cr)
    roe = (p["pat"] / max(p["equity"], 1.0)) * 100.0
    roce = (p["ebit"] / max(p["assets"] - p["cl"], 1.0)) * 100.0
    roa = (p["pat"] / max(p["assets"], 1.0)) * 100.0
    de = p["debt"] / max(p["equity"], 1.0)
    debt_rate = (p["int_exp"] / max(p["debt"], 1.0)) * 100.0 if p["debt"] > 0 else 0.0
    int_cov = p["ebit"] / max(p["int_exp"], 1.0)

    return df, {
        "atr": atr, "rs_alpha": rs_alpha, "sl_px": sl_px, "tech_target": tech_target,
        "qty": qty, "pos_val": pos_val, "max_risk_inr": max_risk_inr,
        "vol_1m_avg": vol_1m_avg, "vol_surge": vol_surge, "deliv_shares_1m": deliv_shares_1m, "deliv_val_1m_cr": deliv_val_1m_cr,
        "tot_mcap_cr": tot_mcap_cr, "retail_pct": retail_pct, "prom_val_cr": prom_val_cr,
        "fii_val_cr": fii_val_cr, "dii_val_cr": dii_val_cr, "retail_val_cr": retail_val_cr,
        "curr_pe": curr_pe, "curr_peg": curr_peg, "fwd_eps": fwd_eps,
        "fair_px_pe": fair_px_by_pe, "fair_px_peg": fair_px_by_peg, "blended_fair": blended_fair_px,
        "roe": roe, "roce": roce, "roa": roa, "de": de, "debt_rate": debt_rate, "int_cov": int_cov
    }

with st.sidebar:
    st.header("1. Sync Any NSE Stock")
    pick_mode = st.radio("Selection Mode", ["Popular Nifty/F&O List", "Type Any NSE Symbol"], horizontal=True)
    if pick_mode == "Popular Nifty/F&O List":
        sym = st.selectbox("Select NSE Stock", NSE_POPULAR)
    else:
        raw_sym = st.text_input("Enter NSE Symbol (e.g. TATAPOWER, IRCTC, BEL)", value="TATAPOWER").strip().upper()
        sym = raw_sym if raw_sym.endswith(".NS") else f"{raw_sym}.NS"

    if "nse_state" not in st.session_state or st.session_state.get("nse_sym") != sym:
        try:
            h_df, n_df, s_dict = sync_nse_full(sym)
            st.session_state.nse_state = (h_df, n_df, s_dict)
            st.session_state.nse_sym = sym
        except Exception as ex:
            st.error(f"Could not sync {sym}: {ex}")
            st.stop()

    if st.button("🔄 Re-Sync Live NSE Data"):
        st.cache_data.clear()
        st.session_state.pop("nse_sym", None)
        st.rerun()

    hist_df, nifty_df, d = st.session_state.nse_state

    st.header("2. Editable P/E & PEG Assumptions")
    cmp = st.number_input("Current Market Price (₹)", value=float(d["cmp"]), step=5.0)
    eps = st.number_input("Trailing EPS (₹)", value=float(d["eps"]), step=1.0)
    eps_g = st.slider("Expected EPS Growth (%)", 2.0, 50.0, float(min(max(d["eps_g"], 2.0), 50.0)), 0.5)
    base_pe_est = round(cmp / max(eps, 0.1), 1)
    edit_pe = st.number_input("Target / Edited P/E Ratio (x)", value=float(np.clip(base_pe_est, 5.0, 100.0)), step=0.5)
    edit_peg = st.number_input("Target / Edited PEG Ratio", value=round(float(np.clip(base_pe_est / max(eps_g, 1.0), 0.3, 5.0)), 2), step=0.05)

    st.header("3. Shares Outstanding, FII/DII/Retail & Delivery")
    shares_cr = st.number_input("Total Outstanding Shares (Cr)", value=float(d["shares_cr"]), step=1.0)
    prom_pct = st.slider("Promoter Holding (%)", 0.0, 75.0, float(min(d["prom_pct"], 75.0)), 0.5)
    fii_pct = st.slider("FII / FPI Holding (%)", 0.0, 60.0, float(min(d["fii_pct"], 60.0)), 0.5)
    dii_pct = st.slider("DII / Mutual Fund Holding (%)", 0.0, 50.0, float(min(d["dii_pct"], 50.0)), 0.5)
    deliv_pct = st.slider("1-Month Avg NSE Delivery / Demat (%)", 10.0, 95.0, 52.0, 1.0)

    st.header("4. Positional Risk & Sizing (₹)")
    capital = st.number_input("Trading Capital (₹)", value=1000000, step=50000)
    risk_pct = st.slider("Max Risk per Trade (%)", 0.5, 3.0, 1.0, 0.25)
    atr_mult = st.slider("Stop-Loss ATR Multiplier", 1.0, 3.0, 1.8, 0.1)
    rr = st.slider("Technical Risk-Reward (1 : R)", 1.5, 5.0, 2.5, 0.5)

    st.header("5. ROE, ROCE & Debt Inputs (₹ Cr)")
    ebit = st.number_input("Operating Profit EBIT (₹ Cr)", value=float(d["ebit"]), step=100.0)
    pat = st.number_input("Net Profit PAT (₹ Cr)", value=float(d["pat"]), step=100.0)
    equity = st.number_input("Shareholders Equity (₹ Cr)", value=float(d["equity"]), step=200.0)
    assets = st.number_input("Total Assets (₹ Cr)", value=float(d["assets"]), step=500.0)
    cl = st.number_input("Current Liabilities (₹ Cr)", value=float(d["cl"]), step=200.0)
    debt = st.number_input("Total Debt (₹ Cr)", value=float(d["debt"]), step=100.0)
    int_exp = st.number_input("Interest Expense (₹ Cr)", value=float(d["int_exp"]), step=25.0)

params = {"cmp": cmp, "eps": eps, "eps_g": eps_g, "edit_pe": edit_pe, "edit_peg": edit_peg,
          "shares_cr": shares_cr, "prom_pct": prom_pct, "fii_pct": fii_pct, "dii_pct": dii_pct, "deliv_pct": deliv_pct,
          "capital": capital, "risk_pct": risk_pct, "atr_mult": atr_mult, "rr": rr,
          "ebit": ebit, "pat": pat, "equity": equity, "assets": assets, "cl": cl, "debt": debt, "int_exp": int_exp}
chart_df, res = run_nse_calculations(hist_df, nifty_df, params)

def rsi_tag(v):
    return "Overbought (>70)" if v >= 70 else ("Oversold (<30)" if v <= 30 else ("Bullish (>55)" if v >= 55 else "Neutral/Weak"))

st.subheader(f"⏱️ {sym} — Multi-Timeframe RSI (15m, 1H, 1D, 1W) & 1-Month Volume / Delivery Demat")
r1, r2, r3, r4, r5, r6 = st.columns(6)
r1.metric("15-Min RSI (14)", f"{d['rsi_15m']}", rsi_tag(d["rsi_15m"]))
r2.metric("1-Hour RSI (14)", f"{d['rsi_1h']}", rsi_tag(d["rsi_1h"]))
r3.metric("1-Day RSI (14)", f"{d['rsi_1d']}", rsi_tag(d["rsi_1d"]))
r4.metric("1-Week RSI (14)", f"{d['rsi_1w']}", rsi_tag(d["rsi_1w"]))
r5.metric("1M Avg Daily Volume", f"{res['vol_1m_avg']:,.0f}", f"Last Surge: {res['vol_surge']:.2f}x")
r6.metric("1M Avg Delivery (Demat)", f"₹ {res['deliv_val_1m_cr']:,.1f} Cr/day", f"{res['deliv_shares_1m']:,.0f} Shs ({deliv_pct:.0f}%)")

st.divider()
st.subheader(f"💎 {sym} — Editable P/E & PEG Fair Price Derivation (All Values in ₹ INR)")
up_pe = ((res["fair_px_pe"] - cmp) / max(cmp, 0.1)) * 100.0
up_peg = ((res["fair_px_peg"] - cmp) / max(cmp, 0.1)) * 100.0
up_blend = ((res["blended_fair"] - cmp) / max(cmp, 0.1)) * 100.0

v1, v2, v3, v4, v5 = st.columns(5)
v1.metric("Current Market Price (CMP)", f"₹ {cmp:,.2f}", f"Fwd EPS: ₹ {res['fwd_eps']:.2f}")
v2.metric("Fair Price @ Edited P/E", f"₹ {res['fair_px_pe']:,.2f}", f"{up_pe:+.1f}% (P/E: {edit_pe:.1f}x)")
v3.metric("Fair Price @ Edited PEG", f"₹ {res['fair_px_peg']:,.2f}", f"{up_peg:+.1f}% (PEG: {edit_peg:.2f})")
v4.metric("Blended Fair Target (₹)", f"₹ {res['blended_fair']:,.2f}", f"{up_blend:+.1f}% vs CMP")
v5.metric("Current P/E & PEG", f"{res['curr_pe']:.1f}x | {res['curr_peg']:.2f}", f"63D RS vs Nifty: {res['rs_alpha']:+.1f}%")

st.subheader("🏦 ROE, ROCE, Debt Cost, Asset Quality & Positional Sizing (₹)")
p1, p2, p3, p4, p5, p6 = st.columns(6)
p1.metric("ROE (%)", f"{res['roe']:.1f}%", f"PAT: ₹ {pat:,.0f} Cr")
p2.metric("ROCE (%)", f"{res['roce']:.1f}%", f"EBIT: ₹ {ebit:,.0f} Cr")
p3.metric("Asset Quality (ROA)", f"{res['roa']:.1f}%", f"Assets: ₹ {assets:,.0f} Cr")
p4.metric("Debt/Eq & Debt Rate", f"{res['de']:.2f}x | {res['debt_rate']:.1f}%", f"Int. Cov: {res['int_cov']:.1f}x")
p5.metric("ATR Stop-Loss (₹)", f"₹ {res['sl_px']:,.2f}", f"14D ATR: ₹ {res['atr']:.1f}")
p6.metric("Position Size (Qty)", f"{res['qty']:,} Shares", f"Exposure: ₹ {res['pos_val']:,.0f}")

st.subheader(f"🏛️ Outstanding Shares & FII / DII / Retail (Client) Holding Value (Total MCap: ₹ {res['tot_mcap_cr']:,.0f} Cr)")
own_df = pd.DataFrame([
    {"Shareholder Category": "Promoters & Group", "Holding (%)": prom_pct, "Shares (Cr)": round(shares_cr * prom_pct / 100, 2), "Value (₹ Cr)": round(res["prom_val_cr"], 1)},
    {"Shareholder Category": "FII / FPI (Foreign Institutions)", "Holding (%)": fii_pct, "Shares (Cr)": round(shares_cr * fii_pct / 100, 2), "Value (₹ Cr)": round(res["fii_val_cr"], 1)},
    {"Shareholder Category": "DII / Mutual Funds / Insurance", "Holding (%)": dii_pct, "Shares (Cr)": round(shares_cr * dii_pct / 100, 2), "Value (₹ Cr)": round(res["dii_val_cr"], 1)},
    {"Shareholder Category": "Retail & HNI Clients (Public)", "Holding (%)": res["retail_pct"], "Shares (Cr)": round(shares_cr * res["retail_pct"] / 100, 2), "Value (₹ Cr)": round(res["retail_val_cr"], 1)}
])
oc1, oc2 = st.columns([1.2, 1])
with oc1:
    st.dataframe(own_df, use_container_width=True, hide_index=True)
with oc2:
    st.bar_chart(own_df.set_index("Shareholder Category")[["Value (₹ Cr)"]])

st.subheader(f"🕯️ {sym} — 1-Year Candlestick Chart with 200, 63 & 14 Moving Averages (₹)")
fig = go.Figure()
fig.add_trace(go.Candlestick(x=chart_df.index, open=chart_df["Open"], high=chart_df["High"], low=chart_df["Low"], close=chart_df["Close"], name="Price (₹)"))
fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["MA14"], line=dict(color="#f59e0b", width=1.4), name="14 MA"))
fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["MA63"], line=dict(color="#3b82f6", width=1.8), name="63 MA (Quarter)"))
fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["MA200"], line=dict(color="#8b5cf6", width=2.1), name="200 MA"))
fig.add_hline(y=res["sl_px"], line_dash="dash", line_color="#ef4444", annotation_text=f"ATR SL: ₹{res['sl_px']:,.1f}")
fig.add_hline(y=res["blended_fair"], line_dash="dash", line_color="#10b981", annotation_text=f"Edited P/E-PEG Fair Price: ₹{res['blended_fair']:,.1f}")
fig.update_layout(height=540, xaxis_rangeslider_visible=False, template="plotly_white", yaxis_title="Price (₹ INR)", margin=dict(l=10, r=10, t=25, b=10))
st.plotly_chart(fig, use_container_width=True)

xl_buf = io.BytesIO()
with pd.ExcelWriter(xl_buf, engine="openpyxl") as w:
    own_df.to_excel(w, sheet_name="Ownership_Value_INR", index=False)
    pd.DataFrame([{"Symbol": sym, "CMP_INR": cmp, "Edited_PE": edit_pe, "Edited_PEG": edit_peg, "Blended_Fair_INR": round(res["blended_fair"], 2), "RSI_15m": d["rsi_15m"], "RSI_1h": d["rsi_1h"], "RSI_1D": d["rsi_1d"], "RSI_1W": d["rsi_1w"], "Vol_1M_Avg": round(res["vol_1m_avg"]), "Deliv_Val_1M_Cr": round(res["deliv_val_1m_cr"], 2), "ROE_%": round(res["roe"], 2), "ROCE_%": round(res["roce"], 2)}]).to_excel(w, sheet_name="Valuation_and_RSI", index=False)
st.download_button("⬇ Download Complete INR Valuation, Ownership & RSI Report (.xlsx)", xl_buf.getvalue(), f"{sym}_Complete_INR_Report.xlsx")
