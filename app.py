import io
import pandas as pd
import streamlit as st
from reconciler import reconcile, generate_demo_data

st.set_page_config(page_title="Payment Reconciliation", page_icon="🔎", layout="wide")
st.title("🔎 Payment Reconciliation & Gap Detection")
st.caption("Compare payment-platform transactions with bank settlements and explain month-end differences.")

with st.sidebar:
    st.header("Reconciliation settings")
    tolerance = st.number_input("Per-transaction rounding tolerance", min_value=0.0, value=0.01, step=0.01, format="%.2f")
    st.caption("Amounts are compared within the same currency. The default tolerance is one cent.")
    demo = st.button("Load generated demo data", use_container_width=True)

if "tx" not in st.session_state or demo:
    tx, bank = generate_demo_data()
    st.session_state.tx, st.session_state.bank = tx, bank

c1, c2 = st.columns(2)
with c1:
    st.subheader("Platform transactions")
    tx_file = st.file_uploader("Upload transactions CSV", type=["csv"], key="tx_upload")
    if tx_file:
        st.session_state.tx = pd.read_csv(tx_file)
    st.dataframe(st.session_state.tx, use_container_width=True, height=230)
with c2:
    st.subheader("Bank settlements")
    bank_file = st.file_uploader("Upload settlements CSV", type=["csv"], key="bank_upload")
    if bank_file:
        st.session_state.bank = pd.read_csv(bank_file)
    st.dataframe(st.session_state.bank, use_container_width=True, height=230)

if st.button("Run reconciliation", type="primary", use_container_width=True):
    try:
        result = reconcile(st.session_state.tx, st.session_state.bank, tolerance=tolerance)
        st.session_state.result = result
    except Exception as exc:
        st.error(f"Could not reconcile these files: {exc}")

if "result" in st.session_state:
    r = st.session_state.result
    st.divider()
    st.header("Reconciliation results")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Platform rows", len(st.session_state.tx))
    m2.metric("Bank rows", len(st.session_state.bank))
    m3.metric("Exceptions", len(r["exceptions"]))
    m4.metric("Currencies", r["summary"]["currencies"])
    st.subheader("Exception breakdown")
    if r["exceptions"].empty:
        st.success("No exceptions detected under the current assumptions.")
    else:
        counts = r["exceptions"]["issue_type"].value_counts().rename_axis("Issue").reset_index(name="Count")
        st.bar_chart(counts.set_index("Issue"))
        st.dataframe(r["exceptions"], use_container_width=True, height=360)
        st.download_button("Download exceptions CSV", r["exceptions"].to_csv(index=False).encode(), "reconciliation_exceptions.csv", "text/csv")
    st.subheader("Currency-level control totals")
    st.dataframe(r["control_totals"], use_container_width=True)
    st.download_button("Download control totals CSV", r["control_totals"].to_csv(index=False).encode(), "control_totals.csv", "text/csv")
    st.info("A detected exception is an investigation lead, not proof of fraud or a bank error. Review source records before posting adjustments.")
