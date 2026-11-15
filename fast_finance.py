import io
import numpy as np
import pandas as pd
import requests
import streamlit as st
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

st.set_page_config(page_title="Instant Financial Analyzer & Ratio Engine", layout="wide")
st.title("Instant Financial Statement Analyzer, Ratio Engine & Fast AI")
st.caption("Sub-second offline search & automated financial ratios - plus optional 1-second Groq AI summaries.")

@st.cache_data(show_spinner=False)
def index_documents(file_data):
    chunks, tables = [], {}
    for name, raw_bytes in file_data:
        low = name.lower()
        if low.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(raw_bytes))
            for i, page in enumerate(reader.pages):
                txt = page.extract_text() or ""
                for para in [p.strip() for p in txt.split("\n\n") if len(p.strip()) > 30]:
                    chunks.append({"source": f"{name} (Page {i+1})", "text": para})
        elif low.endswith((".xlsx", ".xls")):
            xl = pd.ExcelFile(io.BytesIO(raw_bytes))
            for sheet in xl.sheet_names:
                df = xl.parse(sheet).dropna(how="all")
                tables[f"{name} - {sheet}"] = df
                for idx, row in df.iterrows():
                    row_str = " | ".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
                    if row_str:
                        chunks.append({"source": f"{name} ({sheet}, Row {idx+2})", "text": row_str})
        elif low.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(raw_bytes)).dropna(how="all")
            tables[name] = df
            for idx, row in df.iterrows():
                row_str = " | ".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
                if row_str:
                    chunks.append({"source": f"{name} (Row {idx+2})", "text": row_str})
    return chunks, tables

def detect_value(tables, keywords):
    for df in tables.values():
        num_cols = df.select_dtypes(include="number").columns.tolist()
        if not num_cols:
            continue
        val_col = num_cols[-1]
        for _, row in df.iterrows():
            row_text = " ".join([str(v).lower() for v in row.values if pd.notna(v)])
            if any(k in row_text for k in keywords) and pd.notna(row[val_col]):
                return float(row[val_col])
    return 0.0

def ask_groq_fast(api_key, context, question):
    url = "https://groq.com"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are a senior financial analyst. Answer concisely using ONLY the provided financial excerpts."},
            {"role": "user", "content": f"EXCERPTS:\n{context}\n\nQUESTION: {question}"}
        ],
        "temperature": 0.1
    }
    r = requests.post(url, headers=headers, json=payload, timeout=20)
    r.raise_for_status()
    return r.json()["choices"]["message"]["content"]

with st.sidebar:
    st.header("Upload & Speed Settings")
    uploaded = st.file_uploader("Upload Financial Files (PDF, XLSX, CSV)", type=["pdf", "xlsx", "xls", "csv"], accept_multiple_files=True)
    groq_key = st.text_input("Optional: Free Groq API Key", type="password")

if uploaded:
    file_payload = tuple((f.name, f.getvalue()) for f in uploaded)
    chunks, tables = index_documents(file_payload)
    st.success(f"Instantly indexed {len(chunks):,} rows/paragraphs and {len(tables)} table(s).")

    rev = st.number_input("Revenue / Sales", value=detect_value(tables, ["revenue", "total income", "sales"]) or 1000000.0)
    ebitda = st.number_input("Operating Profit / EBITDA", value=detect_value(tables, ["ebitda", "operating profit"]) or 220000.0)
    pat = st.number_input("Net Profit (PAT)", value=detect_value(tables, ["net profit", "profit after tax", "pat"]) or 145000.0)
    ta = st.number_input("Total Assets", value=detect_value(tables, ["total assets"]) or 1500000.0)
    ca = st.number_input("Current Assets", value=detect_value(tables, ["current assets"]) or 600000.0)
    cl = st.number_input("Current Liabilities", value=detect_value(tables, ["current liabilities"]) or 300000.0)
    debt = st.number_input("Total Debt", value=detect_value(tables, ["total debt", "borrowings", "loan"]) or 400000.0)
    eq = st.number_input("Shareholders Equity", value=detect_value(tables, ["equity", "net worth"]) or 800000.0)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Current Ratio", f"{(ca / cl):.2f}x" if cl else "N/A")
    m2.metric("Debt-to-Equity", f"{(debt / eq):.2f}x" if eq else "N/A")
    m3.metric("Operating Margin", f"{(ebitda / rev * 100):.1f}%" if rev else "N/A")
    m4.metric("Net Profit Margin", f"{(pat / rev * 100):.1f}%" if rev else "N/A")
    m5.metric("Return on Assets", f"{(pat / ta * 100):.1f}%" if ta else "N/A")

    ratio_report = pd.DataFrame([
        {"Metric": "Revenue", "Value": rev},
        {"Metric": "EBITDA", "Value": ebitda},
        {"Metric": "Net Profit", "Value": pat},
        {"Metric": "Current Ratio", "Value": round(ca / cl, 2) if cl else 0},
        {"Metric": "Debt-to-Equity", "Value": round(debt / eq, 2) if eq else 0},
        {"Metric": "Operating Margin %", "Value": round(ebitda / rev * 100, 2) if rev else 0},
        {"Metric": "Net Margin %", "Value": round(pat / rev * 100, 2) if rev else 0},
        {"Metric": "ROA %", "Value": round(pat / ta * 100, 2) if ta else 0},
    ])
    xl_buf = io.BytesIO()
    with pd.ExcelWriter(xl_buf, engine="openpyxl") as writer:
        ratio_report.to_excel(writer, sheet_name="Financial_Ratios", index=False)
        for t_name, t_df in list(tables.items())[:5]:
            t_df.to_excel(writer, sheet_name=t_name[:28].replace("/", "_"), index=False)
    st.download_button("Download Full Financial Ratio Report (Excel .xlsx)", xl_buf.getvalue(), "Financial_Analysis_Report.xlsx")

    if tables:
        with st.expander("View Uploaded Statement Tables & Totals"):
            sel = st.selectbox("Choose Statement Table", list(tables.keys()))
            df = tables[sel]
            st.dataframe(df.head(30), use_container_width=True)

    st.divider()
    st.subheader("Instant Statement Search & Q&A")
    query = st.text_input("Ask any question or search any line item:")
    if query and chunks:
        texts = [c["text"] for c in chunks]
        vec = TfidfVectorizer(stop_words="english").fit(texts + [query])
        scores = cosine_similarity(vec.transform([query]), vec.transform(texts)).flatten()
        top_idx = np.argsort(scores)[::-1][:6]
        matched = [chunks[i] for i in top_idx if scores[i] > 0.04]
        if groq_key and matched:
            try:
                ctx = "\n\n".join([f"[{m['source']}]\n{m['text']}" for m in matched])
                st.success(ask_groq_fast(groq_key, ctx, query))
            except Exception as e:
                st.warning(f"Groq error: {e}")
        for idx in top_idx:
            if scores[idx] > 0.04:
                st.markdown(f"**{chunks[idx]['source']}** *(Match: {scores[idx]*100:.0f}%)*")
                st.info(chunks[idx]["text"])
else:
    st.info("Upload Balance Sheets, P&L Statements, or Bank Statements (PDF, XLSX, CSV) in the left sidebar.")
