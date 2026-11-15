import json, os, urllib.parse
from datetime import datetime
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Kanira Advisor | Institutional Wealth & Derivatives Portal", page_icon="🏛️", layout="wide")

BRAND_NAME = "Kanira Advisor"
PARTNER_TAG = "Authorized Business Partner — Mirae Asset Sharekhan • Mumbai & Mira-Bhayandar"
PORTAL_URL = "https://streamlit.app"
WHATSAPP_NO = "919702767077"
GSHEET_WEBHOOK = "https://script.google.com/macros/s/AKfycbwJQqdo0iVqeKRdGnAkyfK4j0P63N8dPgUXuTowqsZMhxiJk1Dy8nwl23e_ngctunU/exec"
USER_DB_FILE = "kanira_users.json"

st.markdown('''<style>
.hero-box {
    background: linear-gradient(135deg, #0b1f3a 0%, #163a6b 60%, #f37021 140%);
    padding: 2.2rem 2.5rem; border-radius: 14px; color: #ffffff;
    box-shadow: 0 10px 28px rgba(11, 31, 58, 0.22); margin-bottom: 1.5rem;
}
.hero-badge {
    display: inline-block; background: rgba(255,255,255,0.16); border: 1px solid rgba(255,255,255,0.28);
    padding: 4px 14px; border-radius: 20px; font-size: 0.82rem; font-weight: 600; letter-spacing: 0.5px; margin-bottom: 0.6rem;
}
.hero-title { font-size: 2.15rem; font-weight: 800; margin: 0.2rem 0; line-height: 1.2; }
.hero-sub { font-size: 1.02rem; opacity: 0.92; margin-top: 0.4rem; }
.feat-card {
    background: #ffffff; border: 1px solid #e2e8f0; border-top: 4px solid #f37021;
    border-radius: 10px; padding: 1.1rem 1.2rem; box-shadow: 0 4px 12px rgba(0,0,0,0.04); height: 100%;
}
.feat-card h4 { color: #0b1f3a; margin: 0 0 0.4rem 0; font-size: 1.05rem; }
.feat-card p { color: #475569; font-size: 0.88rem; margin: 0; line-height: 1.45; }
div[data-testid="stMetric"] {
    background: #f8fafc; border: 1px solid #e2e8f0; border-left: 4px solid #0b1f3a;
    padding: 12px 16px; border-radius: 8px;
}
</style>''', unsafe_allow_html=True)

DEFAULT_USERS = {
    "admin": {"pass": "kanira2026", "role": "Advisor Admin", "name": "Kanira Advisory Desk", "phone": WHATSAPP_NO, "active": True},
    "client": {"pass": "hni2026", "role": "HNI Wealth Client", "name": "Privileged HNI Client", "phone": "", "active": True}
}

def load_users():
    users = dict(DEFAULT_USERS)
    if GSHEET_WEBHOOK.startswith("https://"):
        try:
            rows = requests.get(f"{GSHEET_WEBHOOK}?sheet=Users", timeout=8).json()
            for r in rows[1:]:
                if len(r) >= 4 and str(r).strip():
                    u = str(r).strip().lower()
                    users[u] = {"pass": str(r), "role": str(r), "name": str(r), "phone": str(r) if len(r) > 4 else "", "active": str(r).upper() != "FALSE" if len(r) > 5 else True}
            return users
        except Exception:
            pass
    if os.path.exists(USER_DB_FILE):
        try:
            with open(USER_DB_FILE, "r", encoding="utf-8") as f:
                users.update(json.load(f))
        except Exception:
            pass
    return users

def save_new_user(uname, uinfo):
    if GSHEET_WEBHOOK.startswith("https://"):
        try:
            requests.post(GSHEET_WEBHOOK, json={"sheet": "Users", "action": "append", "row": [uname, uinfo["pass"], uinfo["role"], uinfo["name"], uinfo["phone"], "TRUE"]}, timeout=8)
        except Exception:
            pass
    cur = load_users()
    cur[uname] = uinfo
    with open(USER_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(cur, f, indent=2)

def save_lead(name, phone, interest):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    if GSHEET_WEBHOOK.startswith("https://"):
        try:
            requests.post(GSHEET_WEBHOOK, json={"sheet": "Leads", "action": "append", "row": [ts, name, phone, interest]}, timeout=8)
        except Exception:
            pass
    pd.DataFrame([{"Timestamp": ts, "Name": name, "Phone": phone, "Interest": interest}]).to_csv("kanira_portal_leads.csv", mode="a", header=not os.path.exists("kanira_portal_leads.csv"), index=False)

users_db = load_users()
if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

if not st.session_state.auth_user:
    st.markdown(f'''<div class="hero-box">
        <div class="hero-badge">SEBI-REGISTERED SUB-BROKER PARTNER • INSTITUTIONAL ANALYTICS SUITE</div>
        <div class="hero-title">{BRAND_NAME} — Wealth, Equity & Derivatives Terminal</div>
        <div class="hero-sub">{PARTNER_TAG}</div>
    </div>''', unsafe_allow_html=True)

    f1, f2, f3, f4 = st.columns(4)
    f1.markdown('<div class="feat-card"><h4>📈 2-Month F&O & Greeks</h4><p>Live NSE futures fair value, calendar spreads, all 5 Option Greeks & custom-days 52W P&L.</p></div>', unsafe_allow_html=True)
    f2.markdown('<div class="feat-card"><h4>🇮🇳 NSE Positional & Valuation</h4><p>Editable P/E & PEG fair price, 200/63/14 MAs, multi-timeframe RSI & FII/DII ownership value.</p></div>', unsafe_allow_html=True)
    f3.markdown('<div class="feat-card"><h4>📊 HNI Portfolio & Stress-Test</h4><p>0-100 Portfolio Health Rating, crash simulations, XIRR & capital-gains tax harvesting.</p></div>', unsafe_allow_html=True)
    f4.markdown('<div class="feat-card"><h4>🛡️ Covered Call & Collar Desk</h4><p>Generate monthly option yield on Demat holdings or lock in zero-cost downside floors.</p></div>', unsafe_allow_html=True)

    st.write("")
    col_login, col_lead = st.columns([1, 1.2], gap="large")
    with col_login:
        with st.form("login_form"):
            st.subheader("🔐 Client & Advisor Sign In")
            u = st.text_input("Username", placeholder="Enter your assigned username").strip().lower()
            p = st.text_input("Password", type="password", placeholder="Enter your password")
            if st.form_submit_button("🚀 Unlock Institutional Terminal", use_container_width=True, type="primary"):
                if u in users_db and users_db[u].get("active", True) and users_db[u]["pass"] == p:
                    st.session_state.auth_user = {**users_db[u], "username": u}
                    st.rerun()
                else:
                    st.error("Invalid or inactive credentials. Request access on the right.")
            st.caption("Demo Access: `client` / `hni2026` (HNI Tier) • `admin` / `kanira2026` (Advisor)")

    with col_lead:
        with st.form("lead_form"):
            st.subheader("📞 Request Client Login or Free Portfolio Review")
            l_name = st.text_input("Full Name", placeholder="e.g. Amit Deshmukh")
            l_phone = st.text_input("Mobile / WhatsApp Number (+91)", placeholder="e.g. 9820012345")
            l_service = st.selectbox("Access / Service Requested", ["HNI Wealth Client Login", "F&O Trader Terminal Login", "Free Portfolio Health Rating", "Free Sharekhan Demat Setup"])
            if st.form_submit_button("📲 Submit & Connect on WhatsApp", use_container_width=True):
                if l_name and l_phone:
                    save_lead(l_name, l_phone, l_service)
                    msg = f"Hello {BRAND_NAME}, I am {l_name} ({l_phone}). Please create my login / book consultation for *{l_service}*."
                    st.success("Request logged! Click below to confirm on WhatsApp:")
                    st.markdown(f"[👉 Open WhatsApp Confirmation](https://wa.me{WHATSAPP_NO}?text={urllib.parse.quote(msg)})")
                else:
                    st.warning("Please enter both your Name and Mobile Number.")
    st.stop()

user = st.session_state.auth_user
with st.sidebar:
    st.markdown(f"### 🏛️ {BRAND_NAME}")
    st.success(f"👤 **{user['name']}**  \nTier: `{user['role']}`")
    if user["role"] == "Advisor Admin":
        with st.expander("👥 Create & Share Client Logins"):
            with st.form("add_user_form"):
                new_name = st.text_input("Client Full Name")
                new_phone = st.text_input("Client WhatsApp (with 91)")
                new_u = st.text_input("Assign Username").strip().lower()
                new_p = st.text_input("Assign Password", value="kanira@123")
                new_role = st.selectbox("Access Tier", ["HNI Wealth Client", "F&O Trader", "Advisor Admin"])
                if st.form_submit_button("💾 Save to Cloud & Share"):
                    if new_u and new_p and new_name:
                        save_new_user(new_u, {"pass": new_p, "role": new_role, "name": new_name, "phone": new_phone.strip(), "active": True})
                        st.success(f"Saved `{new_u}`!")
                        st.rerun()
            for uname, uinfo in users_db.items():
                invite_txt = f"Hello {uinfo['name']}, welcome to *{BRAND_NAME} Portal*!\n🔗 Link: {PORTAL_URL}\n👤 User: `{uname}`\n🔑 Pass: `{uinfo['pass']}`"
                wa_target = f"https://wa.me{uinfo['phone']}" if uinfo.get("phone") else "https://wa.me"
                st.markdown(f"**{uinfo['name']}** (`{uname}`) — [📲 Share]({wa_target}?text={urllib.parse.quote(invite_txt)})")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.auth_user = None
        st.rerun()
    st.divider()

ALL_TOOLS = [
    ("nse_positional_pro.py", "🇮🇳 NSE Positional & P/E-PEG Terminal", "Analytics", ["Advisor Admin", "F&O Trader"]),
    ("option_dashboard.py", "📈 2-Month Futures & Option Greeks", "Derivatives", ["Advisor Admin", "F&O Trader", "HNI Wealth Client"]),
    ("hedging_desk.py", "🛡️ HNI Covered Call & Collar Hedging", "Derivatives", ["Advisor Admin", "F&O Trader", "HNI Wealth Client"]),
    ("portfolio_builder.py", "📊 Portfolio Rating & Wealth Builder", "Wealth & HNI", ["Advisor Admin", "HNI Wealth Client"]),
    ("hni_wealth_suite.py", "🏛️ HNI Crash Stress-Test & XIRR", "Wealth & HNI", ["Advisor Admin", "HNI Wealth Client"]),
    ("fast_finance.py", "⚡ Financial Statement & Ratio Engine", "Research", ["Advisor Admin"])
]

nav_dict = {sec: [] for _, _, sec, _ in ALL_TOOLS}
for fname, title, sec, roles in ALL_TOOLS:
    if user["role"] in roles and os.path.exists(fname):
        nav_dict[sec].append(st.Page(fname, title=title))
nav_dict = {k: v for k, v in nav_dict.items() if v}

if nav_dict:
    st.navigation(nav_dict).run()
