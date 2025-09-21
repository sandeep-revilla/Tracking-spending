# app.py
import streamlit as st
import pandas as pd
import json
from google.oauth2.service_account import Credentials
import gspread
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Live Expense Tracker", layout="wide")

st.title("💸 Live Expense Tracker (Google Sheets → Streamlit)")

# --- Sidebar: inputs ---
st.sidebar.header("Google Sheet connection")
SHEET_ID = st.sidebar.text_input("Google Sheet ID (between /d/ and /edit)", "")
SHEET_NAME = st.sidebar.text_input("Worksheet name (e.g. History Transactions)", "History Transactions")
refresh = st.sidebar.button("Refresh now")

st.sidebar.markdown("---")
st.sidebar.markdown("**Instructions:** Put your Google service account JSON in Streamlit Secrets under `gcp_service_account` (see README). Share the sheet with the service account email.")

# --- Helper: get credentials from Streamlit secrets ---
@st.cache_data(ttl=300)
def get_gspread_client():
    # Streamlit Secrets must contain a key "gcp_service_account".
    # In the Streamlit Cloud UI paste the entire service-account JSON under this key.
    if "gcp_service_account" not in st.secrets:
        st.error("Service account JSON not found in Streamlit Secrets. See instructions in the README/sidebar.")
        raise st.StopException

    creds_obj = st.secrets["gcp_service_account"]
    # If the JSON is stored as a string, parse it; if already a mapping, use it.
    if isinstance(creds_obj, str):
        creds_info = json.loads(creds_obj)
    else:
        creds_info = creds_obj

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = Credentials.from_service_account_info(creds_info, scopes=scopes)
    gc = gspread.authorize(credentials)
    return gc

# --- Fetch sheet into DataFrame ---
@st.cache_data(ttl=60)
def load_sheet(sheet_id: str, sheet_name: str):
    if not sheet_id:
        st.warning("Enter Google Sheet ID in the left panel to load data.")
        return pd.DataFrame()

    gc = get_gspread_client()
    try:
        sh = gc.open_by_key(sheet_id)
    except Exception as e:
        st.error(f"Unable to open sheet: {e}")
        return pd.DataFrame()

    try:
        ws = sh.worksheet(sheet_name)
    except Exception:
        # fallback to first worksheet
        ws = sh.get_worksheet(0)

    records = ws.get_all_records(empty2zero=False, head=1)
    df = pd.DataFrame.from_records(records)
    return df

# Reload if user clicks refresh
if refresh:
    st.experimental_rerun()

df = load_sheet(SHEET_ID, SHEET_NAME)

if df.empty:
    st.info("No data loaded yet. Provide Sheet ID and ensure worksheet has rows/headers.")
    st.stop()

# --- Data cleaning (best-effort) ---
st.subheader("Raw data preview")
st.dataframe(df.head(10), use_container_width=True)

# Attempt to find useful columns
col_candidates = {c.lower(): c for c in df.columns}
# common columns in your Excel: DateTime, Date, Bank, Type, Amount, Message, Suspicious
date_col = col_candidates.get("datetime") or col_candidates.get("date") or None
amount_col = col_candidates.get("amount") or col_candidates.get("amt") or None
type_col = col_candidates.get("type") or None
bank_col = col_candidates.get("bank") or None
message_col = col_candidates.get("message") or None
suspicious_col = col_candidates.get("suspicious") or None

# Make a working copy
work = df.copy()

# Parse amount
if amount_col:
    work["Amount"] = pd.to_numeric(work[amount_col], errors="coerce")
else:
    work["Amount"] = pd.to_numeric(work.select_dtypes(include=["number"]).iloc[:, 0], errors="coerce")

# Parse datetime
if date_col:
    try:
        work["DateTime"] = pd.to_datetime(work[date_col], errors="coerce")
    except Exception:
        work["DateTime"] = pd.to_datetime(work[date_col].astype(str), errors="coerce")
else:
    # try to detect a datetime-like column automatically
    for c in work.columns:
        try:
            tmp = pd.to_datetime(work[c], errors="coerce")
            if tmp.notna().sum() > 0:
                work["DateTime"] = tmp
                break
        except Exception:
            continue

work["Date"] = pd.to_datetime(work["DateTime"]).dt.date
work["Month"] = pd.to_datetime(work["DateTime"]).dt.to_period("M").astype(str)
work["Weekday"] = pd.to_datetime(work["DateTime"]).dt.day_name()

# Normalize type (debit/credit)
if type_col:
    work["Type"] = work[type_col].astype(str).str.lower().str.strip()
else:
    # heuristics: if Amount negative -> debit
    work["Type"] = "unknown"
    work.loc[work["Amount"] < 0, "Type"] = "debit"
    work.loc[work["Amount"] > 0, "Type"] = "credit"

# If amounts are positive for both, assume 'debit' comes from a column or message
# (You can improve with rules later)

# Basic filters
valid_types = work["Type"].isin(["debit", "credit"])
if not valid_types.any():
    # try to infer from a column with 'deb' or 'cred'
    work["Type"] = work[type_col].astype(str).str.lower().apply(
        lambda x: "debit" if "deb" in x else ("credit" if "cred" in x else "unknown")
    )

# --- Summaries ---
st.markdown("---")
st.header("Summary metrics")
col1, col2, col3, col4 = st.columns(4)
total_debit = work.loc[work["Type"] == "debit", "Amount"].sum()
total_credit = work.loc[work["Type"] == "credit", "Amount"].sum()
txn_count = len(work)
last_update = work["DateTime"].max()

col1.metric("Total Spent (Debit)", f"{total_debit:,.2f}")
col2.metric("Total Credit", f"{total_credit:,.2f}")
col3.metric("Transactions", txn_count)
col4.metric("Latest txn", str(last_update) if pd.notna(last_update) else "N/A")

# --- Charts layout ---
st.markdown("---")
st.subheader("Interactive charts")

# Daily spending trend
daily = work[work["Type"] == "debit"].groupby("Date")["Amount"].sum().reset_index()
if not daily.empty:
    fig1 = px.line(daily, x="Date", y="Amount", title="Daily Spending (debits)", markers=True)
    st.plotly_chart(fig1, use_container_width=True)

# Monthly
monthly = work.groupby(["Month", "Type"])["Amount"].sum().reset_index()
if not monthly.empty:
    monthly_pivot = monthly.pivot(index="Month", columns="Type", values="Amount").fillna(0).reset_index()
    fig2 = px.bar(monthly_pivot, x="Month", y=[c for c in monthly_pivot.columns if c!="Month"],
                  title="Monthly Debit vs Credit (stacked)", barmode="stack")
    st.plotly_chart(fig2, use_container_width=True)

# Top merchants from message (simple heuristic)
if message_col:
    work["merchant"] = work[message_col].astype(str).str.extract(r"To\s+([A-Za-z0-9 &\.-]{3,50})", expand=False)
    top_merchants = work.groupby("merchant")["Amount"].sum().sort_values(ascending=False).head(10).reset_index()
    if not top_merchants.empty and top_merchants["merchant"].notna().any():
        fig3 = px.bar(top_merchants, x="merchant", y="Amount", title="Top merchants by spend (heuristic)")
        st.plotly_chart(fig3, use_container_width=True)

# Weekday average spend
weekday = work[work["Type"] == "debit"].groupby("Weekday")["Amount"].mean().reindex(
    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
).reset_index()
if not weekday["Amount"].isna().all():
    fig4 = px.bar(weekday, x="Weekday", y="Amount", title="Average spend by weekday")
    st.plotly_chart(fig4, use_container_width=True)

# Bank wise
if bank_col:
    bank = work.groupby([bank_col, "Type"])["Amount"].sum().reset_index()
    if not bank.empty:
        fig5 = px.bar(bank, x=bank_col, y="Amount", color="Type", barmode="group", title="Bank-wise Debit vs Credit")
        st.plotly_chart(fig5, use_container_width=True)

# Transaction size distribution
hist = work[work["Type"] == "debit"]["Amount"].dropna()
if not hist.empty:
    fig6 = px.histogram(hist, x=hist, nbins=30, title="Distribution of debit transaction amounts")
    st.plotly_chart(fig6, use_container_width=True)

# Show cleaned table and allow CSV export
st.markdown("---")
st.subheader("Cleaned transactions (preview)")
st.dataframe(work.head(200), use_container_width=True)

csv = work.to_csv(index=False).encode("utf-8")
st.download_button("Download cleaned CSV", data=csv, file_name="transactions_cleaned.csv", mime="text/csv")

st.markdown("---")
st.caption("App reads your Google Sheet live whenever the page is loaded or refreshed.")
